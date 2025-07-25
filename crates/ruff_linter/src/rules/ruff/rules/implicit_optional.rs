use std::fmt;

use anyhow::{Context, Result};

use ruff_macros::{ViolationMetadata, derive_message_formats};

use ruff_python_ast::name::Name;
use ruff_python_ast::{self as ast, Expr, Operator, Parameters};
use ruff_text_size::{Ranged, TextRange};

use crate::checkers::ast::Checker;
use crate::{Edit, Fix, FixAvailability, Violation};

use ruff_python_ast::PythonVersion;

use crate::rules::ruff::typing::type_hint_explicitly_allows_none;

/// ## What it does
/// Checks for the use of implicit `Optional` in type annotations when the
/// default parameter value is `None`.
///
/// ## Why is this bad?
/// Implicit `Optional` is prohibited by [PEP 484]. It is confusing and
/// inconsistent with the rest of the type system.
///
/// It's recommended to use `Optional[T]` instead. For Python 3.10 and later,
/// you can also use `T | None`.
///
/// ## Example
/// ```python
/// def foo(arg: int = None):
///     pass
/// ```
///
/// Use instead:
/// ```python
/// from typing import Optional
///
///
/// def foo(arg: Optional[int] = None):
///     pass
/// ```
///
/// Or, for Python 3.10 and later:
/// ```python
/// def foo(arg: int | None = None):
///     pass
/// ```
///
/// If you want to use the `|` operator in Python 3.9 and earlier, you can
/// use future imports:
/// ```python
/// from __future__ import annotations
///
///
/// def foo(arg: int | None = None):
///     pass
/// ```
///
/// ## Limitations
///
/// Type aliases are not supported and could result in false negatives.
/// For example, the following code will not be flagged:
/// ```python
/// Text = str | bytes
///
///
/// def foo(arg: Text = None):
///     pass
/// ```
///
/// ## Options
/// - `target-version`
/// - `lint.future-annotations`
///
/// ## Preview
///
/// When [preview] is enabled, if [`lint.future-annotations`] is set to `true`,
/// `from __future__ import annotations` will be added if doing so would allow using the `|`
/// operator on a Python version before 3.10.
///
/// ## Fix safety
///
/// This fix is always marked as unsafe because it can change the behavior of code that relies on
/// type hints, and it assumes the default value is always appropriate—which might not be the case.
///
/// [PEP 484]: https://peps.python.org/pep-0484/#union-types
#[derive(ViolationMetadata)]
pub(crate) struct ImplicitOptional {
    conversion_type: ConversionType,
}

impl Violation for ImplicitOptional {
    const FIX_AVAILABILITY: FixAvailability = FixAvailability::Sometimes;

    #[derive_message_formats]
    fn message(&self) -> String {
        "PEP 484 prohibits implicit `Optional`".to_string()
    }

    fn fix_title(&self) -> Option<String> {
        let ImplicitOptional { conversion_type } = self;
        Some(format!("Convert to `{conversion_type}`"))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ConversionType {
    /// Conversion using the `|` operator e.g., `str | None`
    BinOpOr,
    /// Conversion using the `typing.Optional` type e.g., `typing.Optional[str]`
    Optional,
}

impl fmt::Display for ConversionType {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::BinOpOr => f.write_str("T | None"),
            Self::Optional => f.write_str("Optional[T]"),
        }
    }
}

impl From<PythonVersion> for ConversionType {
    fn from(target_version: PythonVersion) -> Self {
        if target_version >= PythonVersion::PY310 {
            Self::BinOpOr
        } else {
            Self::Optional
        }
    }
}

/// Generate a [`Fix`] for the given [`Expr`] as per the [`ConversionType`].
fn generate_fix(checker: &Checker, conversion_type: ConversionType, expr: &Expr) -> Result<Fix> {
    match conversion_type {
        ConversionType::BinOpOr => {
            let new_expr = Expr::BinOp(ast::ExprBinOp {
                left: Box::new(expr.clone()),
                op: Operator::BitOr,
                right: Box::new(Expr::NoneLiteral(ast::ExprNoneLiteral::default())),
                range: TextRange::default(),
                node_index: ruff_python_ast::AtomicNodeIndex::dummy(),
            });
            let content = checker.generator().expr(&new_expr);
            let edit = Edit::range_replacement(content, expr.range());
            if checker.target_version() < PythonVersion::PY310 {
                Ok(Fix::unsafe_edits(
                    edit,
                    [checker.importer().add_future_import()],
                ))
            } else {
                Ok(Fix::unsafe_edit(edit))
            }
        }
        ConversionType::Optional => {
            let importer = checker
                .typing_importer("Optional", PythonVersion::lowest())
                .context("Optional should be available on all supported Python versions")?;
            let (import_edit, binding) = importer.import(expr.start())?;
            let new_expr = Expr::Subscript(ast::ExprSubscript {
                range: TextRange::default(),
                node_index: ruff_python_ast::AtomicNodeIndex::dummy(),
                value: Box::new(Expr::Name(ast::ExprName {
                    id: Name::new(binding),
                    ctx: ast::ExprContext::Store,
                    range: TextRange::default(),
                    node_index: ruff_python_ast::AtomicNodeIndex::dummy(),
                })),
                slice: Box::new(expr.clone()),
                ctx: ast::ExprContext::Load,
            });
            let content = checker.generator().expr(&new_expr);
            Ok(Fix::unsafe_edits(
                Edit::range_replacement(content, expr.range()),
                [import_edit],
            ))
        }
    }
}

/// RUF013
pub(crate) fn implicit_optional(checker: &Checker, parameters: &Parameters) {
    for parameter in parameters.iter_non_variadic_params() {
        let Some(Expr::NoneLiteral(_)) = parameter.default() else {
            continue;
        };
        let Some(annotation) = parameter.annotation() else {
            continue;
        };

        if let Expr::StringLiteral(string_expr) = annotation {
            // Quoted annotation.
            if let Ok(parsed_annotation) = checker.parse_type_annotation(string_expr) {
                let Some(expr) = type_hint_explicitly_allows_none(
                    parsed_annotation.expression(),
                    checker,
                    checker.target_version(),
                ) else {
                    continue;
                };

                let conversion_type = checker.target_version().into();

                let mut diagnostic =
                    checker.report_diagnostic(ImplicitOptional { conversion_type }, expr.range());
                if parsed_annotation.kind().is_simple() {
                    diagnostic.try_set_fix(|| generate_fix(checker, conversion_type, expr));
                }
            }
        } else {
            // Unquoted annotation.
            let Some(expr) =
                type_hint_explicitly_allows_none(annotation, checker, checker.target_version())
            else {
                continue;
            };

            let conversion_type = if checker.target_version() >= PythonVersion::PY310
                || checker.settings().future_annotations()
            {
                ConversionType::BinOpOr
            } else {
                ConversionType::Optional
            };

            let mut diagnostic =
                checker.report_diagnostic(ImplicitOptional { conversion_type }, expr.range());
            diagnostic.try_set_fix(|| generate_fix(checker, conversion_type, expr));
        }
    }
}
