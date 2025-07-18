//! Run all code and documentation generation steps.

use anyhow::Result;

use crate::{
    generate_cli_help, generate_docs, generate_json_schema, generate_ty_cli_reference,
    generate_ty_env_vars_reference, generate_ty_options, generate_ty_rules, generate_ty_schema,
};

pub(crate) const REGENERATE_ALL_COMMAND: &str = "cargo dev generate-all";

#[derive(clap::Args)]
pub(crate) struct Args {
    #[arg(long, default_value_t, value_enum)]
    mode: Mode,
}

#[derive(Copy, Clone, PartialEq, Eq, clap::ValueEnum, Default)]
pub(crate) enum Mode {
    /// Update the content in the `configuration.md`.
    #[default]
    Write,

    /// Don't write to the file, check if the file is up-to-date and error if not.
    Check,

    /// Write the generated help to stdout.
    DryRun,
}

impl Mode {
    pub(crate) const fn is_dry_run(self) -> bool {
        matches!(self, Mode::DryRun)
    }
}

pub(crate) fn main(args: &Args) -> Result<()> {
    generate_json_schema::main(&generate_json_schema::Args { mode: args.mode })?;
    generate_ty_schema::main(&generate_ty_schema::Args { mode: args.mode })?;
    generate_cli_help::main(&generate_cli_help::Args { mode: args.mode })?;
    generate_docs::main(&generate_docs::Args {
        dry_run: args.mode.is_dry_run(),
    })?;
    generate_ty_options::main(&generate_ty_options::Args { mode: args.mode })?;
    generate_ty_rules::main(&generate_ty_rules::Args { mode: args.mode })?;
    generate_ty_cli_reference::main(&generate_ty_cli_reference::Args { mode: args.mode })?;
    generate_ty_env_vars_reference::main(&generate_ty_env_vars_reference::Args {
        mode: args.mode,
    })?;
    Ok(())
}
