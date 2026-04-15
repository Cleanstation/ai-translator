# Repo Organization Policy

This public repository keeps only documentation that is safe and useful for external readers.

## Keep in this repo

- architecture notes about the tool itself
- generic integration guidance
- public-safe templates and examples
- user-facing setup and usage instructions

## Do not keep in this repo

- host-specific operations
- private downstream repository notes
- rollout journals and transient implementation plans
- secret paths, private endpoints, or machine-local details

## Where internal material should go instead

Use one of these:
- a private notes repository
- a private infrastructure repository
- a private dotfiles repository
- machine-local, non-versioned files

## Working rule

If a document answers “how does this project work for public users?”, it may belong here.
If it answers “how do I operate my private environment?”, it should live elsewhere.
