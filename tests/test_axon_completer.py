import unittest

from prompt_toolkit.document import Document

from ui.axon_completer import AtPathCompleter, AxonInputCompleter, _active_at_token


class AtTokenTests(unittest.TestCase):
    def test_active_at_token(self) -> None:
        self.assertTrue(_active_at_token("read @src"))
        self.assertTrue(_active_at_token("@"))
        self.assertFalse(_active_at_token("/help"))
        self.assertFalse(_active_at_token("email@test.com"))


class AtPathCompleterTests(unittest.TestCase):
    def test_completions_after_at(self) -> None:
        completer = AtPathCompleter()
        doc = Document("@", 1)
        items = list(completer.get_completions(doc, None))
        self.assertGreater(len(items), 0)
        for c in items:
            label = c.text if isinstance(c.text, str) else str(c.text)
            self.assertTrue(label or c.display is not None)


class AxonInputCompleterTests(unittest.TestCase):
    def test_slash_commands(self) -> None:
        completer = AxonInputCompleter()
        doc = Document("/h", 2)
        items = list(completer.get_completions(doc, None))
        self.assertTrue(any("/help" in (c.text or "") for c in items))

    def test_at_over_slash_when_in_at_token(self) -> None:
        completer = AxonInputCompleter()
        doc = Document("use @", 5)
        items = list(completer.get_completions(doc, None))
        self.assertGreater(len(items), 0)


if __name__ == "__main__":
    unittest.main()
