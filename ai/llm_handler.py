import anthropic

class LLMHandler:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def generate_schematic(self, prompt):
        """
        Takes a text description and returns
        schematic generation instructions
        """
        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a PCB schematic expert.
                    Generate KiCad schematic instructions for: {prompt}
                    Return component list and connections in detail."""
                }
            ]
        )
        return message.content[0].text

    def suggest_placement(self, components):
        """
        Takes a list of components and suggests
        optimal placement strategy
        """
        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a PCB layout expert.
                    Suggest optimal placement for these components: {components}
                    Consider signal integrity, thermal management, and routing."""
                }
            ]
        )
        return message.content[0].text

    def check_manufacturing(self, board_info):
        """
        Takes board info and checks for
        manufacturing issues
        """
        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a PCB manufacturing expert.
                    Check these board specifications for issues: {board_info}
                    Return any manufacturing concerns or violations."""
                }
            ]
        )
        return message.content[0].text