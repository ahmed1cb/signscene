class Message:
    def __init__(self, type: str, content: str, mine=True) -> None:
        self.type = type
        self.mine = True
        self.content = content
