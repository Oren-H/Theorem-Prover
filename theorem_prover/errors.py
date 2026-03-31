"""Typed exceptions for the theorem prover."""


class InvalidCommand(Exception):
    """Input does not match any known command name."""


class InvalidInput(Exception):
    """An argument fails Num, Term, or Prop validation."""


class TypeMismatch(Exception):
    """mp() antecedent does not match the supplied Prop."""
