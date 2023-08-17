import chess
import requests
import trio
from kivy.app import async_runTouchApp
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from plyer import vibrator

UNIT = 0.2
DIT = UNIT * 1
DAH = UNIT * 3
INTRA_SPACE = UNIT * 1
INTER_SPACE = UNIT * 3


class Sixer:
    def __init__(self, depth: int = 13) -> None:
        self.depth = depth
        self.board = chess.Board()
        self.buffer = []

    def reset(self) -> None:
        self.board.reset()

    def buffer_reset(self) -> None:
        self.buffer = []

    def buffer_0(self) -> None:
        self.buffer.append("0")

    def buffer_1(self) -> None:
        self.buffer.append("1")

    def get_move_pattern(self, move: chess.Move) -> str:
        sb = []
        to_square = move.to_square
        capture_prev = (
            self.board.move_stack and move.to_square == self.board.peek().to_square
        )
        if capture_prev:
            sb.append("00")
        else:
            sq_inp = self.input_square(to_square, self.side == chess.BLACK)
            sb.append(sq_inp)
        legal_moves = list(
            self.board.generate_legal_moves(to_mask=chess.BB_SQUARES[to_square])
        )
        assert legal_moves, "No moves with to square"
        if len(legal_moves) > 1:
            piece = self.board.piece_type_at(move.from_square)
            piece_inp = self.input_piece(piece)
            sb.append(piece_inp)
            legal_moves = [
                legal_move
                for legal_move in legal_moves
                if self.board.piece_type_at(legal_move.from_square) == piece
            ]
            assert legal_moves, "No moves with piece"
            if len(legal_moves) > 1:
                assert len(legal_moves) == 2, "More than two duplicate pieces"
                higher = int(
                    move == sorted(legal_moves, key=lambda move: move.from_square)[1]
                )
                higher_inp = self.input_higher(higher, self.side == chess.BLACK)
                sb.append(higher_inp)
        return " ".join(sb)

    async def vibrate(self, pattern: str = "0") -> None:
        # import time

        vibrate_pattern = []
        for i, c in enumerate(pattern):
            if c == " ":
                continue
            vibrate_pattern.append(
                0 if i == 0 else INTER_SPACE if pattern[i - 1] == " " else INTRA_SPACE
            )
            vibrate_pattern.append(DIT if c == "0" else DAH)
        # for pause, vibrate in zip(vibrate_pattern[::2], vibrate_pattern[1::2]):
        #     await trio.sleep(pause)
        #     t0 = time.time()
        #     i = 0
        #     while time.time() - t0 < vibrate:
        #         print(f"Brr {i}")
        #         i += 1
        vibrator.pattern(vibrate_pattern)

    def get_best_move(self) -> chess.Move:
        url = f"https://stockfish.online/api/stockfish.php?fen={self.board.fen()}&depth={self.depth}&mode=bestmove"
        response = requests.get(url)
        uci = response.json()["data"].split()[1]
        move = chess.Move.from_uci(uci)
        return move

    async def get_opp_move(self) -> chess.Move:
        while len(self.buffer) < 6:
            await trio.sleep(0.1)
        sq_inp = "".join(self.buffer[:6])
        self.buffer_reset()
        to_square = self.square_input(sq_inp, self.side == chess.BLACK)
        legal_moves = list(
            self.board.generate_legal_moves(to_mask=chess.BB_SQUARES[to_square])
        )
        assert legal_moves, "No moves with to square"
        if len(legal_moves) > 1:
            await self.vibrate()
            while len(self.buffer) < 3:
                await trio.sleep(0.1)
            piece_inp = "".join(self.buffer[:3])
            self.buffer_reset()
            piece = self.piece_input(piece_inp)
            legal_moves = [
                legal_move
                for legal_move in legal_moves
                if self.board.piece_type_at(legal_move.from_square) == piece
            ]
            assert legal_moves, "No moves with piece"
            if len(legal_moves) > 1:
                assert len(legal_moves) == 2, "More than two duplicate pieces"
                await self.vibrate()
                while len(self.buffer) < 1:
                    await trio.sleep(0.1)
                higher_inp = "".join(self.buffer[:1])
                self.buffer_reset()
                higher = self.higher_input(higher_inp, self.side == chess.BLACK)
                legal_moves.sort(key=lambda move: move.from_square)
                legal_moves = legal_moves[higher:]
        return legal_moves[0]

    async def run(self) -> None:
        while len(self.buffer) < 1:
            await trio.sleep(0.1)
        self.side = bool(int("".join(self.buffer[:1])))
        self.buffer_reset()
        await self.vibrate()
        while not self.board.is_game_over():
            if self.board.turn == self.side:
                move = self.get_best_move()
                await self.vibrate(self.get_move_pattern(move))
            else:
                move = await self.get_opp_move()
            self.board.push(move)

    @staticmethod
    def input_square(sq: chess.Square, flipped: bool) -> str:
        file, rank = chess.square_file(sq), chess.square_rank(sq)
        if flipped:
            file, rank = 7 - file, 7 - rank
        file_inp, rank_inp = bin(file)[2:].zfill(3), bin(rank)[2:].zfill(3)
        sq_inp = " ".join([file_inp, rank_inp])
        return sq_inp

    @staticmethod
    def input_piece(piece: chess.PieceType) -> str:
        piece_inp = bin(piece)[2:].zfill(3)
        return piece_inp

    @staticmethod
    def input_higher(higher: int, flipped: bool) -> str:
        if flipped:
            higher = 1 - higher
        higher_inp = str(higher)
        return higher_inp

    @staticmethod
    def square_input(sq_inp: str, flipped: bool) -> chess.Square:
        file_inp, rank_inp = sq_inp[0:3], sq_inp[3:6]
        file, rank = int(file_inp, base=2), int(rank_inp, base=2)
        if flipped:
            file, rank = 7 - file, 7 - rank
        square = chess.square(file, rank)
        return square

    @staticmethod
    def piece_input(piece_inp: str) -> chess.PieceType:
        piece_type = chess.PieceType(int(piece_inp, base=2))
        return piece_type

    @staticmethod
    def higher_input(higher_inp: str, flipped: bool) -> int:
        higher = int(higher_inp, base=2)
        if flipped:
            higher = 1 - higher
        return higher


def build(sixer):
    layout = BoxLayout(orientation="horizontal")
    button0, button1 = Button(text="0", font_size=50), Button(text="1", font_size=50)
    layout.add_widget(button0)
    layout.add_widget(button1)
    button0.on_press, button1.on_press = sixer.buffer_0, sixer.buffer_1
    return layout


async def run_app_happily(root, nursery):
    await async_runTouchApp(root, async_lib="trio")
    nursery.cancel_scope.cancel()


if __name__ == "__main__":
    sixer = Sixer()

    async def root_func():
        root = build(sixer)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(run_app_happily, root, nursery)
            nursery.start_soon(sixer.run)

    trio.run(root_func)
