import argparse
import os
import re
import sys
from lxml import etree
from rope.base.project import Project
from rope.refactor.rename import Rename


class rename:

    def __init__(self, project_path=None, module_path=None):
        """ initialize using project path and optional sub module path to limit rename scope """
        if project_path:
            self.project = Project(project_path)
        self.module_path = module_path
        self.words = set()
        self.files = []
        self.namemap = {}
        self.classname_regex = re.compile('class\s+(?P<name>[a-zA-Z0-9_]+)')
        self.methodname_regex = re.compile('def\s+(?P<name>[a-zA-Z0-9_]+)')

    def load_words(self):
        """ load all known words """
        with open('words') as f:
            for line in f:
                self.words.add(line.strip().lower())

    def load_dict(self, dictionary_path):
        """ load a custom dict with new (recognized) and restricted (unrecognized) words """
        doc = etree.parse(dictionary_path)
        for recognized in doc.xpath('/dictionary/recognized/word'):
            self.words.add(recognized.text)
        for unrecognized in doc.xpath('/dictionary/unrecognized/word'):
            if unrecognized.text in self.words:
                self.words.remove(unrecognized.text)

    def wash_word(self, string):
        """ clean up word by separating prefix, suffix and word without underscores """
        prefix = string[:string.find(string.lstrip('_'))]
        suffix = string[len(string.rstrip('_')):]
        word = string.lower().replace('_', '')
        return (prefix, word, suffix)

    def find_word(self, string, index):
        """ find the longest word from index """
        word = ''
        i = index + 1
        while i <= len(string):
            if string[index:i] in self.words:
                word = string[index:i]
            i += 1
        return word

    def reverse_find_word(self, string, index):
        """ backwards find the longest word from index """
        word = ''
        i = index - 1
        while i >= 0:
            if string[i:index] in self.words:
                word = string[i:index]
            i -= 1
        return word

    def find_words(self, string, index=-1):
        """ find all known words in a string """
        words = []
        if index == -1:
            index = len(string)
        if index == 0:
            return words
        word = self.reverse_find_word(string, index)
        if word:
            words.insert(0, word)
            index -= len(word)
        else:
            index -= 1
        w = self.find_words(string, index)
        w.extend(words)
        words = w
        #words.extend(self.find_words(string, index))
        return words

    def rename(self, string):
        """ rename string to PEP8 standard """
        index = 0
        last_index = 0
        new_name = ''
        prefix, old_name, suffix = self.wash_word(string)
        for word in self.find_words(old_name):
            index = old_name.find(word, index)
            if last_index != index:
                new_name += old_name[last_index: index]
            if len(new_name) > 0:
                new_name += '_'
            new_name += word
            index += len(word)
            last_index = index
        if last_index != len(old_name):
            if len(new_name) > 0:
                new_name += '_'
            new_name += old_name[last_index:]
        return '%s%s%s' % (prefix, new_name, suffix)

    def index_file(self, content):
        """ get all indexes for methods to rename in context
            return list of old name, position and new name """
        index = 0
        methods = []
        running = True
        while running:
            method = self.methodname_regex.search(content, index)
            if method:
                old_name = method.group('name')
                pos = method.start() + method.string[method.start():].find(old_name)
                new_name = self.rename(old_name)
                if old_name != new_name:
                    methods.append((old_name, pos, new_name))
                index = pos + len(old_name)
            else:
                running = False
        return methods

    def get_files(self):
        """ iterator for all valid project files """
        for file_resource in self.project.get_files():
            if self.module_path and not self.module_path in file_resource.real_path:
                continue
            yield file_resource

    def dry_run(self):
        """ list all methods to be renamed without updating any files """
        for file_resource in self.get_files():
            methods = self.index_file(file_resource.read())
            print('%s' % file_resource.path)
            for method in methods:
                print('    %s:%d->%s' % (method[0], method[1], method[2]))

    def refactor(self):
        """ renames all methods to PEP8 standard """
        for file_resource in self.get_files():
            while True:
                self.project.validate()
                methods = self.index_file(file_resource.read())
                if len(methods) == 0:
                    break
                method = methods[0]
                old_name = method[0]
                pos = method[1]
                new_name = method[2]
                print('rename: %s:%d->%s' % (old_name, pos, new_name))
                changes = Rename(self.project, file_resource, pos).get_changes(new_name)
                self.project.do(changes)


def validate_path(path):
    """ validate that given path exist """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if not os.path.exists(path):
        print('Invalid path: %s' % path)
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Refactor all method names to follow the PEP8 standard.')
    parser.add_argument('path', metavar='PROJECT_PATH', type=str, nargs=1, help='path to project folder.')
    parser.add_argument('-m', '--module', metavar='MODULE_PATH', type=str, nargs='?', help='path to module folder, (sub path to project scope).')
    parser.add_argument('-n', '--dry-run', dest='dryrun', metavar='', type=bool, nargs='?', default=False, const=True, help='don not refactor any files, just list work order.')
    parser.add_argument('-d', '--dict', metavar='DICTIONARY', type=str, nargs='?', help='path to additional dictionary for un/recognized words.')

    args = parser.parse_args()
    projectpath = args.path[0]
    modulepath = args.module
    dictpath = args.dict
    if not validate_path(projectpath):
        sys.exit(1)
    if modulepath and not validate_path(modulepath):
        sys.exit(2)
    if modulepath and projectpath not in modulepath:
        print('Module: %s not in project: %s' % (modulepath, projectpath))
        sys.exit(3)
    if dictpath and not validate_path(dictpath):
        print('Missing dictionary: %s' % dictpath)

    renamer = rename(projectpath, modulepath)
    renamer.load_words()
    renamer.load_dict(dictpath)
    if args.dryrun:
        renamer.dry_run()
    else:
        renamer.refactor()
