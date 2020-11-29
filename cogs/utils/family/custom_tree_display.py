class CustomTreeDisplay(object):

    def __init__(self, edge=None, node=None, font=None, highlighted_font=None, highlighted_node=None, background=None, direction=None):
        self.edge = edge if edge is not None else 0x0
        self.node = node if node is not None else 0x0
        self.font = font if font is not None else 0xffffff
        self.highlighted_font = highlighted_font if highlighted_font is not None else 0xffffff
        self.highlighted_node = highlighted_node if highlighted_node is not None else 0x0000ff
        self.background = background if background is not None else 0xffffff
        self.direction = direction if direction is not None else "TB"
        self.highlighted_user_id = None

    @classmethod
    async def fetch_custom_tree(cls, db, user_id:int):
        # rows = await db("SELECT edge, node, font, highlighted_font, highlighted_node, background, direction FROM user_settings WHERE user_id=$1", user_id)
        rows = await db("SELECT edge, node, font, highlighted_font, highlighted_node, background, direction FROM customisation WHERE user_id=$1", user_id)
        try:
            row = rows[0]
        except IndexError:
            row = {}
        return cls(**row)

    def get_graphviz_customisation_string(self) -> str:
        current_strings = (
            f"""node[shape=box,fontcolor="{self.int_to_hex_code(self.font)}",color="{self.int_to_hex_code(self.edge)}",fillcolor="{self.int_to_hex_code(self.node)}",style=filled];"""
            f"""edge[dir=none,color="{self.int_to_hex_code(self.edge)}"];"""
            f"""bgcolor="{self.int_to_hex_code(self.background)}";"""
            f"""rankdir="{self.direction}";"""
        )
        if self.highlighted_user_id:
            current_strings += (
                f"""{self.highlighted_user_id}[fillcolor="{self.int_to_hex_code(self.highlighted_node)}",fontcolor="{self.int_to_hex_code(self.highlighted_font)}"];"""
            )
        return current_strings

    @staticmethod
    def int_to_hex_code(value:int):
        if value < 0:
            return "transparent"
        return "#" + format(value, ">06X")
