from uuid import uuid4

class Vote:
    socket: str
    question_uuid: str

    def __init__(self, socket, question_uuid):
        self.socket = socket
        self.question_uuid = question_uuid

class Question:
    uuid: str
    text: str
    votes: list[Vote]

    def __init__(self, text, votes=None, uuid=None):
        self.text = text
        # Maybe initialize with own socket since we are automatically voting for ourselves
        self.votes = [] if votes==None else votes
        self.uuid = str(uuid4()) if uuid==None else uuid

    # Add vote to votes list
    def toggle_vote(self, vote: Vote):
        if self.not_voted_for(vote):
            self.votes.append(vote)
        else:
            for v in self.votes:
                if v.socket == vote.socket:
                    self.votes.remove(v)

    # Verify that one client can only vote once per question
    def not_voted_for(self, vote: Vote):
        for v in self.votes:
            if v.socket == vote.socket:
                return False
        return True 


class ApplicationState:
    def __init__(self, questions: list[Question] = []):
        self.questions: list[Question] = questions

    def get_question_from_uuid(self, uuid: str) -> Question | None:
        for question in self.questions:
            if question.uuid == uuid:
                return question
        return None

    def add_question(self, question: Question):
        self.questions.append(question)

    def get_application_state(self):
        return self.__dict__