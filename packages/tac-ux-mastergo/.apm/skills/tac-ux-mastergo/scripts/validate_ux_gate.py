#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate lightweight gate decisions for tac-ux-mastergo.

Python 3.6+ required.
"""

import argparse
import sys


def as_bool(value):
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError("Expected boolean value, got: {0}".format(value))


def emit(text):
    """Python 3 Unicode 安全输出。"""
    try:
        print(text)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
        else:
            print(text.encode("ascii", errors="replace").decode("ascii"))


def validate_input(args):
    errors = []
    warnings = []

    if args.mode == "A":
        if not args.has_new_truth_source:
            errors.append("Mode A requires new interaction/business truth input.")
        if not args.target_identifiable:
            errors.append("Mode A requires an identifiable page/flow target.")
        if args.has_existing_handoff and not args.has_new_truth_source:
            warnings.append("Existing handoff detected without new truth input; consider Mode C.")
    elif args.mode == "B":
        if not args.has_existing_handoff:
            errors.append("Mode B requires an existing approved handoff.")
        if not args.target_identifiable:
            errors.append("Mode B requires an identifiable target handoff file.")
        if args.has_new_truth_source:
            warnings.append("Mode B should use the approved handoff as truth source, not new interaction input.")
    elif args.mode == "C":
        if not args.has_existing_handoff and not args.has_new_truth_source:
            errors.append("Mode C requires an existing confirmed handoff or new design input.")
    else:
        errors.append("Unsupported mode: {0}".format(args.mode))

    for warning in warnings:
        emit("WARN: {0}".format(warning))
    for error in errors:
        emit("ERROR: {0}".format(error))

    if errors:
        emit("RESULT: pre-blocking")
        emit("FAIL")
        return 1

    emit("RESULT: pass")
    emit("PASS")
    return 0


def validate_interrupt(args):
    if args.has_pre_blocking:
        emit("RESULT: pause-now")
        emit("LEVEL: pre-blocking")
        emit("FAIL")
        return 1

    if args.has_blocking:
        emit("RESULT: pause-at-boundary")
        emit("LEVEL: blocking")
        if args.resume_point:
            emit("RESUME_POINT: {0}".format(args.resume_point))
        emit("FAIL")
        return 1

    if args.has_non_blocking:
        emit("RESULT: continue-with-marking")
        emit("LEVEL: non-blocking")
        emit("PASS")
        return 0

    emit("RESULT: continue")
    emit("LEVEL: clear")
    emit("PASS")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="Validate UX skill gate decisions.")
    subparsers = parser.add_subparsers(dest="command")

    input_parser = subparsers.add_parser("input", help="Validate mode entry gate.")
    input_parser.add_argument("--mode", required=True, choices=["A", "B", "C"])
    input_parser.add_argument("--has-new-truth-source", required=True, type=as_bool)
    input_parser.add_argument("--has-existing-handoff", required=True, type=as_bool)
    input_parser.add_argument("--target-identifiable", required=True, type=as_bool)
    input_parser.set_defaults(func=validate_input)

    interrupt_parser = subparsers.add_parser("interrupt", help="Validate interruption decision.")
    interrupt_parser.add_argument("--has-pre-blocking", required=True, type=as_bool)
    interrupt_parser.add_argument("--has-blocking", required=True, type=as_bool)
    interrupt_parser.add_argument("--has-non-blocking", required=True, type=as_bool)
    interrupt_parser.add_argument("--resume-point", default="")
    interrupt_parser.set_defaults(func=validate_interrupt)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
