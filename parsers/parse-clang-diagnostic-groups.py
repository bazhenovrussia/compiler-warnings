#!/usr/bin/env python2

from __future__ import print_function

import antlr4
import argparse
import sys
import TableGenLexer
import TableGenListener
import TableGenParser


class ClangDiagnosticGroupsListener(TableGenListener.TableGenListener):
    def __init__(self):
        self.currentDefinitionName = None
        self.currentSwitchName = None
        self.currentClassDefinitionName = None
        self.currentReferences = None
        self.switchClassesReferences = {}
        self.switchNames = {}
        self.switchClasses = {}
        self.parentClasses = {}
        self.parentSwitches = {}

    def enterEmptySwitchName(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentSwitchName = ""

    def enterSwitchText(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentSwitchName = ctx.getText()

    def enterDefinitionName(self, ctx):
        self.currentDefinitionName = ctx.getText()

    def exitSwitchDefinition(self, ctx):
        self.currentDefinitionName = None

    def exitClassDefinition(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            if self.currentSwitchName is not None:
                self.switchNames[self.currentSwitchName] = (
                    self.currentDefinitionName)
                self.switchClassesReferences[self.currentSwitchName] = (
                    self.currentReferences)
                for reference in self.currentReferences:
                    parents = self.parentClasses.get(reference, [])
                    parents.append(self.currentSwitchName)
                    self.parentSwitches[reference] = parents
            if self.currentDefinitionName:
                self.switchClasses[self.currentDefinitionName] = (
                    self.currentSwitchName)
                for reference in self.currentReferences:
                    parents = self.parentClasses.get(reference, [])
                    parents.append(self.currentDefinitionName)
                    self.parentClasses[reference] = parents
        self.currentSwitchName = None
        self.currentClassDefinitionName = None
        self.currentReferences = None

    def enterClassDefinitionName(self, ctx):
        self.currentClassDefinitionName = ctx.getText()
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentReferences = []

    def enterIdentifierReference(self, ctx):
        self.currentReferences.append(ctx.getText())


def print_references(diagnostics, switch_name, level):
    references = diagnostics.switchClassesReferences.get(switch_name, [])
    reference_switches = []
    for reference_class_name in references:
        reference_switch_name = diagnostics.switchClasses[reference_class_name]
        reference_switches.append(reference_switch_name)
    for reference_switch_name in sorted(reference_switches):
        print("# %s-W%s" % ("  " * level, reference_switch_name))
        print_references(diagnostics, reference_switch_name, level + 1)


def is_root_class(diagnostics, switch_name):
    # Root class is something that has parents in neither switches nor classes:
    class_name = diagnostics.switchNames[switch_name]
    has_parent_switch = class_name in diagnostics.parentSwitches
    has_parent_class = class_name in diagnostics.parentClasses
    return not has_parent_switch and not has_parent_class


def main(argv):
    parser = argparse.ArgumentParser(
        description="Clang diagnostics group parser")
    parser.add_argument("--top-level", action='store_true', help="""\
Show only top level switches. These filter out all switches that are enabled
by some other switch and that way remove duplicate instances from the output.
""")
    parser.add_argument("--unique", action='store_true', help="""\
Show only unique switches.""")
    parser.add_argument("groups_file", metavar="groups-file", help="""\
The path of clang diagnostic groups file.
""")
    args = parser.parse_args(argv[1:])

    string_input = antlr4.FileStream(args.groups_file)
    lexer = TableGenLexer.TableGenLexer(string_input)
    stream = antlr4.CommonTokenStream(lexer)
    parser = TableGenParser.TableGenParser(stream)
    tree = parser.expression()

    diagnostics = ClangDiagnosticGroupsListener()
    walker = antlr4.ParseTreeWalker()
    walker.walk(diagnostics, tree)

    for name in sorted(diagnostics.switchNames.keys()):
        if args.top_level and not is_root_class(diagnostics, name):
            continue
        print("-W%s" % name)
        if args.unique:
            continue
        print_references(diagnostics, name, 1)


if __name__ == "__main__":
    main(sys.argv)