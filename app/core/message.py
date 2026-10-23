class Message:
    def __init__(self, type: str, content, mine: bool = True) -> None:
        self.type = type
        self.mine = mine
        self.content = content
