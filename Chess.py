'''
----------------------------------------------------------------------------------
Chess.py - a module to be added to a Jasper program
Last edited: 12 March 2020
Creator: Joe Bruckner

Implements a chess API and supports a Chess engine to play against
a brave human player. Classes include a chessmatch which has a board
and players, chess players, a generic chess piece class which is
inherited by all different types of chess pieces (ie. pawn, rook, etc.).
A chess engine class (in work) inherits chess player and makes any random,
legal move
----------------------------------------------------------------------------------
'''

# -*- coding: utf-8-*-
from __future__ import with_statement
from __future__ import absolute_import
import re
import copy
import signal
import os
import random
from client.mic import Mic
from client import jasperpath

# Standard module stuff
WORDS = ["CHESS", "GAME", "PLAY"]

# Globals variables for Chess playing
SIZE = 8
FEN_STARTING = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def handle(text, mic, profile):
	"""
        Responds to user-input, typically speech text, by playing brilliant chess moves.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone
                   number)
    """

	match = ChessMatch()
	mic.say("Very well, best of luck to you sir")

	while True:
		try:
			with WatchdogTimer(300):
				# Player shall be white and move first
				for i in range(10):
					player_move = unicode(mic.activeListen(), "utf-8")
					assert isinstance(player_move, unicode)
					assert player_move is not None
					match_status = match.nextMove(player_move)
					if "Illegal Move" in match_status:
						mic.say(match_status + ", try again kind sir")
					else:
						break
					if i == 9:
						mic.say("Exiting game for my own sanity, too many bad moves")
				
				if match_status is "Checkmate":
					mic.say(match_status)
					break
				# Jasper shall be black and move next
				match_status = match.nextMove(None)
				mic.say(match_status)

		except WatchdogTimer:
			print()

	mic.say("Good game, well played")

def isValid(text):
	"""
        Returns True if the input is related to chess.

        Arguments:
        text -- user-input, typically transcribed speech
    """
	return any(word in text.upper() for word in WORDS)


class WatchdogTimer(Exception):
	"""
		Ensures that the program does not run on indefinately by throwing an exception after the specified time has passed
	"""
	def __init__(self, time=60):
		"""
		Initialize the timer
		:param time: by deafult 60 sec, integer input is seconds before exception thrown
		"""
		self.time = time

	def __enter__(self):
		signal.signal(signal.SIGALRM, self.handler)
		signal.alarm(self.time)

	def __exit__(self, type, value, traceback):
		signal.alarm(0)

	def handler(self, signum, frame):
		raise self

	def __str__(self):
		return "Timeout Error after %ds", self.time


# This is where the fun begins
class ChessMatch(object):
	def __init__(self):
		"""
		Initializes the chess match with all required variables. Its also calls the funstion to setup the board in the
		starting position.
		"""
		self.game_file = "path_to_file"
		self.board = [[0 for x in range(SIZE)] for y in range(SIZE)]

		self.white = ChessPlayer(self, color="WHITE")
		self.black = ChessEngine(self, color="BLACK")
		
		self.move = "WHITE"
		self.half_move = 0
		self.full_move = 0
		
		self.setupPosition(FEN_STARTING)
	
	def setupPosition(self, fen):
		"""
		Decodes the Forsyth–Edwards Notation to setup particular position, this is a standard notation used to describe
		the current position, but has no knowledge of previous moves in the game
		:param fen: the FEN string that is decoded to setup a particular position
		"""
		assert isinstance(fen, unicode)

		rank = SIZE - 1
		file = 0

		# First part of the notation describes which pieces go where
		for fen_char in fen:
			assert (0 <= rank < 8) and (0 <= file <= 8)

			if fen_char == '/':
				rank -= 1
				file = 0
			elif fen_char.isdigit():
				for square in range(int(fen_char,10)):
					self.board[rank][file] = None
					file += 1
			elif fen_char == ' ':
				break
			else:
				if fen_char.isalpha() and fen_char.isupper():
					piece_color = self.white
				elif fen_char.isalnum() and fen_char.islower():
					piece_color = self.black
				else:
					assert False
				
				if fen_char.upper() == 'R':
					self.board[rank][file] = Rook(self, piece_color, rank, file)
				elif fen_char.upper() == 'N':
					self.board[rank][file] = Knight(self, piece_color, rank, file)
				elif fen_char.upper() == 'B':
					self.board[rank][file] = Bishop(self, piece_color, rank, file)
				elif fen_char.upper() == 'Q':
					self.board[rank][file] = Queen(self, piece_color, rank, file)
				elif fen_char.upper() == 'K':
					self.board[rank][file] = King(self, piece_color, rank, file)
				elif fen_char.upper() == 'P':
					self.board[rank][file] = Pawn(self, piece_color, rank, file)
				else:
					assert False

				file += 1

		# Next decode who's turn it is
		fen_info = fen.split(' ')
		if fen_info[1] == "w":
			self.move = "WHITE"
		elif fen_info[1] == "b":
			assert False
			self.move = "BLACK"

		# Also read in the castling privledges
		if 'K' in fen_info[2]:
			self.white.castle_short = True
		else:
			self.white.castle_short = False
		if 'Q' in fen_info[2]:
			self.white.castle_long = True
		else:
			self.white.castle_long = False
		if 'k' in fen_info[2]:
			self.black.castle_short = True
		else:
			self.black.castle_short = True
		if 'q' in fen_info[2]:
			self.black.castle_long = True
		else:
			self.black.castle_long = True

		# Check if any piece is en passantable
		if fen_info[3] != "-":
			# make this piece en passantable, still needs to be included and tested
			NotImplementedError()

		# insert the turn counters
		self.half_move = int(fen_info[4],10)
		self.full_move = int(fen_info[5],10)

	def coordinate_to_notation(self, target_piece, target_location, gives_check):
		"""
		Decodes the move into algebraic notation. This will be used to create a lookup table (of all possible legal
		moves) that will be compared to the move made by a player
		:param target_piece: the piece thats being moved
		:param target_location: the location to where the piece is moving in (rank, file) relative to bottom left corner
		:param gives_check: whether or not the move puts the other play in check
		:return: returns a string corresponding to the algebraic notation for the input
		"""
		assert isinstance(target_piece, ChessPiece)
		assert isinstance(target_location, tuple)
		assert isinstance(gives_check, bool)

		# if piece with same name and you can both go to the same square you need to add the file letter to notation
		# if also the same file, use the rank number. ie Ra-a8 or R8-a8
		# with more than 2 pieces of the same type it may be necessary to have Ra1-a8, which is also accounted for
		rank_specifier = None
		file_specifier = None
		for ranks in self.board:
			for piece in ranks:
				if piece is not None and \
								piece.owner.color == target_piece.owner.color and \
								piece.location is not target_piece.location and \
								piece.__class__.__name__ == target_piece.__class__.__name__ and \
								target_location in piece.mobility():
					if piece.location['rank'] == target_piece.location['rank']:
						file_specifier = chr(ord('a') + target_piece.location['file'])
					elif piece.location['file'] == target_piece.location['file']:
						rank_specifier = chr(target_piece.location['rank'] + 1)
					else:
						file_specifier = chr(ord('a') + target_piece.location['file'])

		# special notation for the pawns, since we say "e4" not "Pe4"
		name = ""
		if target_piece.__class__.__name__ == "Pawn":
			if self.board[target_location[0]][target_location[1]] is not None:
				name = chr(ord('a') + target_piece.location['file']) + "x"

		else:
			# Knight denoted by N, because the king is K
			if target_piece.__class__.__name__ == "Knight":
				name = "N"
			else:
				name = target_piece.__class__.__name__[0]

			if rank_specifier is not None:
				name += rank_specifier
			if file_specifier is not None:
				name += file_specifier

			# operation (ie capture or not)
			if self.board[target_location[0]][target_location[1]] is not None:
				name += "x"

		# target location
		if gives_check is True:
			notation = name + str(chr(ord('a') + target_location[1])) + str(target_location[0] + 1) + "+"
		else:
			notation = name + str(chr(ord('a') + target_location[1])) + str(target_location[0] + 1)
		
		return notation

	def nextMove(self, move):
		"""
		Decides who it is that actually makes the next move
		:param move: the move being played (if legal), or attempting to be played
		:return: string containing the result of the move (ie. legal, illegal, checkmate, etc.)
		"""
		assert (self.move == self.white.color) or (self.move == self.black.color)
		if self.move == self.white.color:
			assert move is not None
			result = self.white.makeMove(move)
			if "Illegal Move" not in result:
				self.move = self.black.color
		else:
			assert move is None
			result = self.black.generateMove()
			if "Illegal Move" not in result:
				self.move = self.white.color
		#assert isinstance(result, str)
		return result


class ChessPlayer(object):
	def __init__(self, parent, color, short_castle=True, long_castle=True):
		"""
		Initialization for chessplayer class
		:param parent: the chess match the chess player is playing in
		:param color: usually white or black
		:param short_castle: whether kingside clastling priveldges exist, true by default
		:param long_castle: whether queenside clastling priveldges exist, true by default
		"""
		assert isinstance(parent, ChessMatch)
		assert isinstance(color, unicode)
		assert isinstance(short_castle, bool)
		assert isinstance(long_castle, bool)

		self.castle_short = short_castle
		self.castle_long = long_castle
		self.prev_castle_short = None
		self.prev_castle_long = None
		self.color = color
		self.parent = parent

		self.availble_moves = []

	def get_availble_moves(self):
		"""
		Adds every availble move the the get_availble_moves list, ensuring that they are legal moves of course
		"""
		self.availble_moves = []
		for ranks in self.parent.board:
			for piece in ranks:
				if piece is not None and piece.owner.color == self.color:
					assert isinstance(piece, ChessPiece)
					possible_moves = piece.mobility()
					for move in possible_moves:
						piece.makeMove(move)
						if not self.inCheck:
							if (self.color == "WHITE" and self.parent.black.inCheck) or (self.color == "BLACK" and self.parent.white.inCheck):
								gives_check = True
							else:
								gives_check = False
							piece.unmakeMove()
							self.availble_moves.append({'piece': piece, 'move': move,
														'notation': self.parent.coordinate_to_notation(piece, move, gives_check)})
						else:
							piece.unmakeMove()

	@property
	def inCheck(self):
		"""
		Evaluates whether the player is in check or not
		:return: True if in check, false if not
		"""
		opponent_moves = []
		kings_position = None

		for player_ranks in self.parent.board:
			for player_piece in player_ranks:
				if player_piece is not None and player_piece.owner.color == self.color and player_piece.__class__.__name__ == "King":
					kings_position = player_piece.location
				elif player_piece is not None and player_piece.owner.color != self.color:
					opponent_moves.append(player_piece.mobility())

		assert kings_position is not None

		flat_opp_moves = []
		for sublist in opponent_moves:
			for item in sublist:
				flat_opp_moves.append(item)

		return (kings_position['rank'], kings_position['file']) in flat_opp_moves

	def makeMove(self, move_input):
		"""
		Specifies the move for a player to make, also checks if the move results in check or checkmate, and whether it
		is a legal mobve or not
		:param move_input: a string of algebraic notation. If its not algebratic notation or not a legal move, the 
			function will handle it, no assertion as to the validity of the string shoule be made
		:return: a string describing the outcome of the move
		"""
		assert isinstance(move_input, str)

		self.get_availble_moves()
		
		if not self.availble_moves and self.inCheck:
			return "Checkmate"
		elif not self.availble_moves:
			return "Draw"
		else:
			for move_search in self.availble_moves:
				if move_search['notation'] == move_input:
					move_search['piece'].makeMove(move_search['move'])
					return move_input

			return "Illegal Move: " + move_input


class ChessEngine(ChessPlayer):
	def generateMove(self):
		"""
		Will eventually use the power of the machine to determine what should be played in a particular position, for
		now it just chooses any random, legal move
		"""

		self.get_availble_moves()
		selection = random.randint(0, len(self.availble_moves) - 1)
		assert self.availble_moves[selection]['notation'] is not None
		return self.makeMove(self.availble_moves[selection]['notation'])

		
class ChessPiece(object):
	def __init__(self, parent, owner, rank, file):
		"""
		Chess piece class, this is the structure for all inhertited types of chess pieces (e.g. Rook, King, etc)
		:param parent: the chess match that the piece is in
		:param owner: the player that controls this piece
		:param rank: the current rank (0-7 int) of the piece
		:param file: the current file (0-7 int) of the piece
		"""
		assert isinstance(parent, ChessMatch)
		assert isinstance(owner, ChessPlayer)
		assert isinstance(rank, int) and (0 <= rank < 8)
		assert isinstance(file, int) and (0 <= rank < 8)

		# default chess piece stuff
		self.active = True
		self.parent = parent
		self.owner = owner
		self.location = {'rank': rank, 'file': file}
		self.possible_moves = []
		self.legal_moves = []
		self.color = None

		self.taken_piece = None
		self.prev_location =  None

	# probe_distance(RANK, FILE) is relative to own square
	def probeSquare(self, probe_distances):
		"""
		Checks for all squares the piece can actually move to, this is a list of squares starting and ending along the
		same path that car concurrently checked to see if a piece can move there. The reason for this is to ensure 
		pieces dont move through one another
		:param probe_distances: list of squares to be sequentially evaluated as to whether a piece can move there
		"""
		assert isinstance(probe_distances, list)

		for probe_distance in probe_distances:
			if 0 <= (self.location['rank'] + probe_distance[0]) < SIZE and 0 <= (self.location['file'] + probe_distance[1]) < SIZE:
				probed_piece = self.parent.board[self.location['rank'] + probe_distance[0]][self.location['file'] + probe_distance[1]]
				if probed_piece is not None and probed_piece.owner.color == self.owner.color:
					assert isinstance(probed_piece, ChessPiece)
					break
				elif probed_piece is not None and probed_piece.owner.color != self.owner.color:
					assert isinstance(probed_piece, ChessPiece)
					self.possible_moves.append((self.location['rank'] + probe_distance[0], self.location['file'] + probe_distance[1]))
					break
				else:
					self.possible_moves.append((self.location['rank'] + probe_distance[0], self.location['file'] + probe_distance[1]))

	def mobility(self):
		"""
		A function all children need to specify how they move, so raise an error if a child does not properly implement
		this function
		"""
		raise NotImplementedError()

	def makeMove(self, square):
		"""
		How a particular piece is moved through the board, we also need to save the last location of this piece, and
		anything it captures by moving so that we may unmove if need by
		:param square: 
		"""
		assert isinstance(square, tuple)
		assert (0 <= self.location['rank'] < SIZE) and (0 <= self.location['file'] < SIZE)

		self.prev_location = copy.copy(self.location)
		self.location['rank'] = square[0]
		self.location['file'] = square[1]

		self.taken_piece = self.parent.board[square[0]][square[1]]
		self.parent.board[square[0]][square[1]] = self
		self.parent.board[self.prev_location['rank']][self.prev_location['file']] = None

	def unmakeMove(self):
		"""
		The unmake move revents the last move this piece made. Is supported and used so we can make a move and check the
		status of the position. This is for check, checkmate, and stalemate evaluations
		"""
		assert (0 <= self.location['rank'] < SIZE) and (0 <= self.location['file'] < SIZE)
		assert (0 <= self.prev_location['rank'] < SIZE) and (0 <= self.prev_location['file'] < SIZE)
		assert self.prev_location is not None

		self.parent.board[self.prev_location['rank']][self.prev_location['file']] = self
		self.parent.board[self.location['rank']][self.location['file']] = self.taken_piece

		# cover your tracks
		self.location = copy.copy(self.prev_location)
		self.prev_location = None
		self.taken_piece = None

	def __str__(self):
		"""
		So the name of the object actially makes sense
		:return: color and name of the piece
		"""
		return str(self.owner.color) + str(self.__class__.__name__)

	def __repr__(self):
		"""
		So the name of the object actially makes sense
		:return: first letter of color and name of the piece
		"""
		return str(self.owner.color[0]) + str(self.__class__.__name__[0])

		
class Pawn(ChessPiece):

	def __init__(self, parent, owner, rank, file):
		"""
		The pawn class, a child of chess piece
		:param parent: the chess match that the piece is in
		:param owner: the player that controls this piece
		:param rank: the current rank (0-7 int) of the piece
		:param file: the current file (0-7 int) of the piece
		"""
		assert isinstance(parent, ChessMatch)
		assert isinstance(owner, ChessPlayer)
		assert isinstance(rank, int) and (0 <= rank < 8)
		assert isinstance(file, int) and (0 <= rank < 8)

		super().__init__(parent, owner, rank, file)
		self.en_passentable = False
		
	def probeSquare(self, probe_ahead=None, probe_diagonal=None, probe_adjacent=None):
		"""
		Probes squares for the pawn, since it caputes differenly than other pieces
		:param probe_ahead: the forwards squares, up or down the board depending on color
		:param probe_diagonal: diagonal squares avaolble for capture if enemy piece is there
		:param probe_adjacent: these squares are only capturable in en passant situations
		"""
		if probe_ahead is None:
			probe_ahead = []
		assert isinstance(probe_ahead, list)

		if probe_diagonal is None:
			probe_diagonal = []
		assert isinstance(probe_diagonal, list)

		if probe_adjacent is None:
			probe_adjacent = []
		assert isinstance(probe_adjacent, list)

		for probe_distance in probe_ahead:
			assert (self.location['rank'] + probe_distance[0]) < SIZE and (self.location['file'] + probe_distance[1]) < SIZE
			probed_piece = self.parent.board[self.location['rank'] + probe_distance[0]][self.location['file'] + probe_distance[1]]
			if probed_piece is not None:
				break
			else:
				self.possible_moves.append((self.location['rank'] + probe_distance[0], self.location['file'] + probe_distance[1]))

		for probe_distance in probe_diagonal:
			assert (self.location['rank'] + probe_distance[0]) < SIZE and (self.location['file'] + probe_distance[1]) < SIZE
			probed_piece = self.parent.board[self.location['rank'] + probe_distance[0]][self.location['file'] + probe_distance[1]]
			if probed_piece is not None and probed_piece.owner.color != self.owner.color:
				self.possible_moves.append((self.location['rank'] + probe_distance[0], self.location['file'] + probe_distance[1]))

		for probe_distance in probe_adjacent:
			assert (self.location['rank'] + probe_distance[0]) < SIZE and (self.location['file'] + probe_distance[1]) < SIZE
			probed_piece = self.parent.board[self.location['rank'] + probe_distance[0]][self.location['file'] + probe_distance[1]]
			if probed_piece is not None and probed_piece.owner.color != self.owner.color and \
					probed_piece.__class__.__name__ == "Pawn" and probed_piece.en_passentable:
				if self.owner.color == "WHITE":
					self.possible_moves.append((self.location['rank'] + probe_distance[0] + 1, self.location['file'] + probe_distance[1]))
				elif self.owner.color == "BLACK":
					self.possible_moves.append((self.location['rank'] + probe_distance[0] - 1, self.location['file'] + probe_distance[1]))
				else:
					assert False

	
	def mobility(self):
		"""
		Specifies the way a pawn can move, ie. two squares up if on the second or seventh ranks and so on
		:return: all potential squares the pawn can move, even if out of bounds or un-capturable
		"""
		assert self.owner.color == "WHITE" or self.owner.color == "BLACK"
		self.possible_moves = []
		if self.owner.color == "WHITE":
			up_down = 1
		else:
			up_down = -1

		assert (0 <= self.location['rank'] < SIZE) and (0 <= self.location['file'] < SIZE)

		# 1 or 2 spaces from starting position
		if self.location['rank'] == 1 or self.location['rank'] == 6:
			if self.location['file'] == 0:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, 1)], [])
			elif self.location['file'] == 7:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, -1)], [])
			else:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, 1),(up_down, -1)], [])

		# en passant availble
		elif self.location['rank'] == 3 or self.location['rank'] == 4:
			if self.location['file'] == 0:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, 1)], [(0, 1)])
			elif self.location['file'] == 7:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, -1)], [(0, -1)])
			else:
				self.probeSquare([(up_down, 0), (2 * up_down, 0)], [(up_down, 1), (up_down, -1)], [(0, 1), (0, -1)])

		# otherwise move normally
		else:
			if self.location['file'] == 0:
				self.probeSquare([(up_down, 0)], [(up_down, 1)], [])
			elif self.location['file'] == 7:
				self.probeSquare([(up_down, 0)], [(up_down, -1)], [])
			else:
				self.probeSquare([(up_down, 0)], [(up_down, 1),(up_down, -1)], [])

		return self.possible_moves


class Rook(ChessPiece):
	
	def mobility(self):
		"""
		Specifies the way a rook can move, ie. along ranks and files (castling is a king move, so no need to 
		handle here)
		:return: all potential squares the rook can move, even if out of bounds or un-capturable
		"""
		self.possible_moves = []

		north, south, east, west = ([],) * 4

		for square in range(1, SIZE):
			north.append((square, 0))
			south.append((-square, 0))
			east.append((0, square))
			west.append((0, -square))

		super().probeSquare(north)
		super().probeSquare(south)
		super().probeSquare(east)
		super().probeSquare(west)

		return self.possible_moves

		
class Knight(ChessPiece):
	
	def mobility(self):
		"""
		Specifies the way a knight can move, ie. two squares up and one accross in any orientation
		:return: all potential squares the knight can move, even if out of bounds or un-capturable
		"""
		self.possible_moves = []

		super().probeSquare([(1,2)])
		super().probeSquare([(2,1)])

		super().probeSquare([(1,-2)])
		super().probeSquare([(2,-1)])

		super().probeSquare([(-1,2)])
		super().probeSquare([(-2,1)])

		super().probeSquare([(-1,-2)])
		super().probeSquare([(-2,-1)])

		return self.possible_moves


class Bishop(ChessPiece):
	
	def mobility(self):
		"""
		Specifies the way a bishop can move, diagonally
		:return: all potential squares the bishop can move, even if out of bounds or un-capturable
		"""
		self.possible_moves = []

		northeast, northwest, southeast, southwest = ([],) * 4

		for square in range(1, SIZE):
			northeast.append((square, square))
			northwest.append((square, -square))
			southeast.append((-square, square))
			southwest.append((-square, -square))

		super().probeSquare(northeast)
		super().probeSquare(northwest)
		super().probeSquare(southeast)
		super().probeSquare(southwest)

		return self.possible_moves


class Queen(ChessPiece):
	
	def mobility(self):
		"""
		Specifies the way a queen can move, so diagonally and across rank and files
		:return: all potential squares the queen can move, even if out of bounds or un-capturable
		"""
		self.possible_moves = []

		north, south, east, west, northeast, northwest, southeast, southwest = ([],) * 8

		for square in range(1, SIZE):
			north.append((square, 0))
			south.append((-square, 0))
			east.append((0, square))
			west.append((0, -square))
			northeast.append((square, square))
			northwest.append((square, -square))
			southeast.append((-square, square))
			southwest.append((-square, -square))

		super().probeSquare(north)
		super().probeSquare(south)
		super().probeSquare(east)
		super().probeSquare(west)
		super().probeSquare(northeast)
		super().probeSquare(northwest)
		super().probeSquare(southeast)
		super().probeSquare(southwest)

		return self.possible_moves
		

class King(ChessPiece):
			
	def mobility(self):
		"""
		Specifies the way a king can move, so one square in any direction or by castling
		:return: all potential squares the king can move, even if out of bounds or un-capturable
		"""
		self.possible_moves = []

		super().probeSquare([(1,0)])
		super().probeSquare([(-1,0)])
		super().probeSquare([(0,1)])
		super().probeSquare([(0,-1)])
		super().probeSquare([(1,1)])
		super().probeSquare([(1,-1)])
		super().probeSquare([(-1,1)])
		super().probeSquare([(-1,1)])

		if self.owner.castle_short and self.owner.color is "WHITE":
			assert self.location['rank'] == 0 and self.location['file'] == 4
			assert isinstance(self.parent.board[0][7], Rook)
			if self.owner.board[0][6] is None and self.owner.board[0][5] is None:
				super().probeSquare([(0, 2)])
		if self.owner.castle_short and self.owner.color is "BLACK":
			assert self.location['rank'] == 7 and self.location['file'] == 4
			assert isinstance(self.parent.board[7][7], Rook)
			if self.owner.board[7][6] is None and self.owner.board[7][5] is None:
				super().probeSquare([(0, 2)])
		if self.owner.castle_long and self.owner.color is "WHITE":
			assert self.location['rank'] == 0 and self.location['file'] == 4
			assert isinstance(self.parent.board[0][0], Rook)
			if self.parent.board[7][1] is None and self.parent.board[7][2] is None and self.parent.board[7][3] is None:
				super().probeSquare([(0, -2)])
		if self.owner.castle_long and self.owner.color is "BLACK":
			assert self.location['rank'] == 7 and self.location['file'] == 4
			assert isinstance(self.parent.board[7][0], Rook)
			if self.parent.board[7][1] is None and self.parent.board[7][2] is None and self.parent.board[7][3] is None:
				super().probeSquare([(0, -2)])

		return self.possible_moves

	def makeMove(self, square):
		"""
		Special function for the king to move, to ensure that he may castle should he please
		:param square: the square the king is moving to, will be the ending location of his position when electing to
			castle
		"""
		assert isinstance(square, tuple)
		assert 0 <= self.location['file'] < SIZE

		super().makeMove(square)
		if square[1] - self.location['file'] == 2:
			assert isinstance(self.parent.board[self.location['rank']][7], Rook)
			assert self.owner.castle_short is True
			self.parent.board[self.location['rank']][7].makeMove((self.location['rank'], 5))
		elif self.location['file'] - square[1] == 3:
			assert isinstance(self.parent.board[self.location['rank']][0], Rook)
			assert self.owner.castle_long is True
			self.parent.board[self.location['rank']][0].makeMove((self.location['rank'], 3))

		self.owner.prev_castle_short = self.owner.castle_short
		self.owner.prev_castle_long = self.owner.castle_long
		self.owner.castle_short = False
		self.owner.castle_long = False

	def unmakeMove(self):
		"""
		Special function for the king to unmake his last move, to ensure that castling is supported
		"""
		assert (0 <= self.prev_location['file'] < SIZE) and (0 <= self.location['file'] < SIZE)

		if self.prev_location['file'] - self.location['file'] == 2:
			assert isinstance(self.parent.board[self.location['rank']][5], Rook)
			assert self.owner.prev_castle_short is True
			self.parent.board[self.location['rank']][5].unmakeMove()
		elif self.location['file'] - self.prev_location['file'] == 3:
			assert isinstance(self.parent.board[self.location['rank']][3], Rook)
			assert self.owner.prev_castle_long is True
			self.parent.board[self.location['rank']][3].unmakeMove()

		self.owner.castle_short = self.owner.prev_castle_short
		self.owner.castle_long = self.owner.prev_castle_long

		super().unmakeMove()
