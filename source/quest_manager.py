class QuestManager:
    def __init__(self, game):
        self.templates = self.load_templates()
        self.active_quests = None # will load active quests from savefile
    
    def load_templates(self):
        pass