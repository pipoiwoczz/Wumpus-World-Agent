
from kb import KnowledgeBase
from agent import Agent
from const import World, AgentState


def load_testcase(filepath: str):
    with open(filepath, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
    size = int(lines[0])
    board = [[{} for _ in range(size)] for _ in range(size)]
    agent_pos = (size-1, 0)

    for i in range(size):
        row = lines[i+1].split('.')
        for j, cell in enumerate(row):
            if 'W' in cell: board[i][j]['wumpus'] = True
            if 'P_G' in cell: board[i][j]['gas'] = True
            if 'H_P' in cell: board[i][j]['potion'] = True
            if 'G' in cell and 'P_G' not in cell: board[i][j]['gold'] = True
            if 'P' in cell and '_G' not in cell and '_P' not in cell: board[i][j]['pit'] = True
            if 'A' in cell: agent_pos = (i, j)

    for i in range(size):
        for j in range(size):
            if board[i][j].get('wumpus', False):
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    if 0 <= i+dx < size and 0 <= j+dy < size:
                        board[i+dx][j+dy]['stench'] = True
            if board[i][j].get('pit', False):
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    if 0 <= i+dx < size and 0 <= j+dy < size:
                        board[i+dx][j+dy]['breeze'] = True
            if board[i][j].get('gas', False):
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    if 0 <= i+dx < size and 0 <= j+dy < size:
                        board[i+dx][j+dy]['whiff'] = True
            if board[i][j].get('potion', False):
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    if 0 <= i+dx < size and 0 <= j+dy < size:
                        board[i+dx][j+dy]['glow'] = True

    return board, agent_pos

if __name__ == '__main__':
    test1 = ["testcase1.txt", "testcase2.txt", "testcase3.txt", "testcase4.txt", "testcase5.txt"]
    test2 = ["testcase6.txt"]
    for testcase in ["testcase4.txt"]:
        print(f"Running testcase: {testcase}")
        
        # Load the board and agent start position from the testcase file
        board, agent_start = load_testcase("input/" + testcase)
        kb = KnowledgeBase(10)
        world = World(board)
        state = AgentState(location=agent_start)
        agent = Agent(world, kb, state, output="output/"+testcase.replace('.txt', ''))

        agent.run() 

