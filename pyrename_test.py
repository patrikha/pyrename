from pyrename import rename
import unittest


class test_pyrename(unittest.TestCase):

    def test_find_words(self):
        r = rename()
        r.words.add('the')
        r.words.add('quick')
        r.words.add('brown')
        r.words.add('fox')
        parts = r.find_words('thequickbrownfox')

        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], 'the')
        self.assertEqual(parts[1], 'quick')
        self.assertEqual(parts[2], 'brown')
        self.assertEqual(parts[3], 'fox')

    def test_find_missing_words(self):
        r = rename()
        r.words.add('fox')
        r.words.add('brown')
        parts = r.find_words('testfoxfoobrownbar')
        self.assertEqual(parts[0], 'fox')
        self.assertEqual(parts[1], 'brown')

    def test_wash_word(self):
        r = rename()
        self.assertEqual(r.wash_word('Test_a_WORD'), ('', 'testaword', ''))
        self.assertEqual(r.wash_word('_Internal'), ('_', 'internal', ''))
        self.assertEqual(r.wash_word('__Private'), ('__', 'private', ''))
        self.assertEqual(r.wash_word('__init__'), ('__', 'init', '__'))

    def test_rename(self):
        r = rename()
        r.words.add('fox')
        r.words.add('brown')
        r.words.add('init')
        r.words.add('internal')
        self.assertEqual(r.rename('thequickbrownfox'), 'thequick_brown_fox')
        self.assertEqual(r.rename('thequickbrownfoxjumps'), 'thequick_brown_fox_jumps')
        self.assertEqual(r.rename('brown_fox'), 'brown_fox')
        self.assertEqual(r.rename('_internal'), '_internal')
        self.assertEqual(r.rename('_internalfox'), '_internal_fox')
        self.assertEqual(r.rename('__privateBROWNfox'), '__private_brown_fox')
        self.assertEqual(r.rename('__init__'), '__init__')

    def test_index_file(self):
        r = rename()
        r.words.add('fox')
        r.words.add('brown')
        methods = r.index_file('class a:\r\n    def testbrownfox(self):\r\n        pass\r\n    def brown_fox(self):\r\n        pass\r\n    def foobar(self):\r\n        pass')
        self.assertEqual(methods[0][0], 'testbrownfox')
        self.assertEqual(methods[0][1], 18)
        self.assertEqual(methods[0][2], 'test_brown_fox')
        self.assertEqual(len(methods), 1)

        methods = r.index_file('class a:\r\n    def foobar(self):\r\n        pass')
        self.assertEqual(len(methods), 0)

        methods = r.index_file('class a:\r\n    def brown_fox(self):\r\n        pass')
        print(methods)
        self.assertEqual(len(methods), 0)

if __name__ == '__main__':
    unittest.main()
