import os
import re
from rope.base.project import Project
from rope.refactor.rename import Rename


class rename:

    def __init__(self):
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

    def find_words(self, string, index=0):
        """ find all known words in a string """
        words = []
        if index == len(string):
            return words
        word = self.find_word(string, index)
        if word:
            words.append(word)
            index += len(word)
        else:
            index += 1
        words.extend(self.find_words(string, index))
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


def main():
    root = os.path.join(os.path.abspath('.'), 'test')
    project = Project(root)
    r = rename()
    r.load_words()
    r.words.remove('testa')
    for file_resource in project.get_files():
        while True:
            project.validate()
            methods = r.index_file(file_resource.read())
            if len(methods) == 0:
                break
            method = methods[0]
            old_name = method[0]
            pos = method[1]
            new_name = method[2]
            print('rename: %s:%d->%s' % (old_name, pos, new_name))
            changes = Rename(project, file_resource, pos).get_changes(new_name)
            project.do(changes)

if __name__ == '__main__':
    main()
