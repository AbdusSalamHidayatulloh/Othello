class TutorialData:
    TUTORIAL_STEPS = [
        {
            'text': ['Welcome to Othello!', 'Get more discs than your', 'opponent by the end.'],
            'board': None,            # None = standard starting board
            'goal': 'next',
        },
        {
            'text': ['Click the highlighted square.', 'You must flip at least', 'one black disc.', '', 'Press the yellow square'],
            'board': None,
            'goal': 'move',
            'player': 1,
            'target': (2, 4),         # the only move we accept (row, col)
        },
        {
            'text': ['The enemy will do the same', 'They must flip atleast', 'one white disc', '', 'Press the yellow square'],
            'board': None,
            'goal': 'move',
            'player': -1,
            'target': (4, 5), 
        },
        {
            'text': ['To win, you need to flip', 'the most disc on the board'],
            'board': None,            # None = standard starting board
            'goal': 'next',
        },
        {
            'text': ["That's all, goodluck!"],
            'board': None,            # None = standard starting board
            'goal': 'next',
        },
]