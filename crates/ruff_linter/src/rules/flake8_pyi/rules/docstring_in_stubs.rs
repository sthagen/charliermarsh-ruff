use ruff_macros::{ViolationMetadata, derive_message_formats};
use ruff_python_ast::ExprStringLiteral;
use ruff_python_semantic::Definition;
use ruff_text_size::Ranged;

use crate::checkers::ast::Checker;
use crate::{AlwaysFixableViolation, Edit, Fix};

/// ## What it does
/// Checks for the presence of docstrings in stub files.
///
/// ## Why is this bad?
/// Stub files should omit docstrings, as they're intended to provide type
/// hints, rather than documentation.
///
/// ## Example
///
/// ```pyi
/// def func(param: int) -> str:
///     """This is a docstring."""
///     ...
/// ```
///
/// Use instead:
///
/// ```pyi
/// def func(param: int) -> str: ...
/// ```
#[derive(ViolationMetadata)]
pub(crate) struct DocstringInStub;

impl AlwaysFixableViolation for DocstringInStub {
    #[derive_message_formats]
    fn message(&self) -> String {
        "Docstrings should not be included in stubs".to_string()
    }

    fn fix_title(&self) -> String {
        "Remove docstring".to_string()
    }
}

/// PYI021
pub(crate) fn docstring_in_stubs(
    checker: &Checker,
    definition: &Definition,
    docstring: Option<&ExprStringLiteral>,
) {
    let Some(docstring_range) = docstring.map(ExprStringLiteral::range) else {
        return;
    };

    let statements = match definition {
        Definition::Module(module) => module.python_ast,
        Definition::Member(member) => member.body(),
    };

    let edit = if statements.len() == 1 {
        Edit::range_replacement("...".to_string(), docstring_range)
    } else {
        Edit::range_deletion(docstring_range)
    };

    let mut diagnostic = checker.report_diagnostic(DocstringInStub, docstring_range);
    diagnostic.set_fix(Fix::unsafe_edit(edit));
}
