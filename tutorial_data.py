TUTORIAL_STEPS = [
    {
        'text': ['Welcome to Othello!', 'Get more discs than your', 'opponent by the end.'],
        'board': None,            # None = standard starting board
        'goal': 'next',
    },
    {
        'text': ['Click the highlighted square.', 'You must flip at least', 'one black disc.'],
        'board': None,
        'goal': 'move',
        'target': (2, 3),         # the only move we accept (row, col)
    },
    {
        'text': ['The enemy will do the same', 'They must flip atleast', 'one white disc'],
        'board': None,
        'goal': 'move',
        'target': (3, 2), 
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