using System;
using System.Collections.Generic;
using ChessLib.Core;
using ChessLib.Logic;
using ChessLib.Pieces;

namespace ChessAI;

public class Bot
{
    private PieceColor _botColor;
    private MoveGenerator _moveGen = null!; 
    private int _depth;

    public Bot(PieceColor botColor, int depth)
    {
        _botColor = botColor;
        _depth = depth;
    }

    public (Position from, Position to) FindBestMove(GameManager game)
    {
        _moveGen = new MoveGenerator(game.State);
        
        int bestScore = _botColor == PieceColor.White ? int.MinValue : int.MaxValue;
        (Position from, Position to) bestMove = (new Position(0,0), new Position(0,0));

        var allMoves = GetAllMoves(game.Board, _botColor);
        if (allMoves.Count == 0) return bestMove; 

        PieceColor nextTurn = _botColor == PieceColor.White ? PieceColor.Black : PieceColor.White;

        int alpha = int.MinValue;
        int beta = int.MaxValue;

        foreach (var move in allMoves)
        {
            var copyBoard = game.Board.Clone();
            copyBoard.Move(move.from, move.to);

            var movedPiece = copyBoard.GetPiece(move.to);
            if (movedPiece != null && movedPiece.Type == PieceType.Pawn)
            {
                if ((movedPiece.Color == PieceColor.White && move.to.Y == 0) || 
                    (movedPiece.Color == PieceColor.Black && move.to.Y == 7))
                {
                    copyBoard.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, movedPiece.Color);
                }
            }

            int score = Minimax(copyBoard, _depth - 1, alpha, beta, nextTurn, game.PositionHistory);

            if (_botColor == PieceColor.White)
            {
                if (score > bestScore) 
                { 
                    bestScore = score; 
                    bestMove = move; 
                }
                alpha = Math.Max(alpha, bestScore); 
            }
            else 
            {
                if (score < bestScore) 
                { 
                    bestScore = score; 
                    bestMove = move; 
                }
                beta = Math.Min(beta, bestScore); 
            }
        }

        return bestMove;
    }

    // Minimax 
    private int Minimax(Board board, int depth, int alpha, int beta, PieceColor currentTurn, Dictionary<string, int> gameHistory)
    {
        var moves = GetAllMoves(board, currentTurn);

        if (moves.Count == 0) 
        {
            if (_moveGen.IsKingInCheck(board, currentTurn))
            {
                return currentTurn == PieceColor.White ? -100000 - depth : 100000 + depth;
            }
            else
            {
                return 0;
            }
        }

        if (depth == 0) 
        {
            int eval = Evaluator.Evaluate(board);
            
            string hash = board.GetBoardString() + currentTurn;
            if (gameHistory.ContainsKey(hash) && gameHistory[hash] >= 1)
            {
                eval += (currentTurn == PieceColor.White ? -50 : 50); 
            }
            
            return eval;
        }

        PieceColor nextTurn = currentTurn == PieceColor.White ? PieceColor.Black : PieceColor.White;

        if (currentTurn == PieceColor.White)
        {
            int maxScore = int.MinValue;
            foreach (var move in moves)
            {
                var copy = board.Clone();
                copy.Move(move.from, move.to);

                var movedPiece = copy.GetPiece(move.to);

                if (movedPiece != null && movedPiece.Type == PieceType.Pawn)
                {
                    if ((movedPiece.Color == PieceColor.White && move.to.Y == 0) || 
                        (movedPiece.Color == PieceColor.Black && move.to.Y == 7))
                    {
                        copy.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, movedPiece.Color);
                    }
                }

                int score = Minimax(copy, depth - 1, alpha, beta, nextTurn, gameHistory);
                maxScore = Math.Max(maxScore, score);
                alpha = Math.Max(alpha, score);
                
                if (beta <= alpha) break;
            }
            return maxScore;
        }
        else
        {
            int minScore = int.MaxValue;
            foreach (var move in moves)
            {
                var copy = board.Clone();
                copy.Move(move.from, move.to);

                var movedPiece = copy.GetPiece(move.to);

                if (movedPiece != null && movedPiece.Type == PieceType.Pawn)
                {
                    if ((movedPiece.Color == PieceColor.White && move.to.Y == 0) || 
                        (movedPiece.Color == PieceColor.Black && move.to.Y == 7))
                    {
                        copy.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, movedPiece.Color);
                    }
                }

                int score = Minimax(copy, depth - 1, alpha, beta, nextTurn, gameHistory);
                minScore = Math.Min(minScore, score);
                beta = Math.Min(beta, score);
                
                if (beta <= alpha) break;
            }
            return minScore;
        }
    }

    // collect all legal moves for current turn
    private List<(Position from, Position to)> GetAllMoves(Board board, PieceColor color)
    {
        var moves = new List<(Position from, Position to)>();
        foreach (var piece in board.GetPiecesOfColor(color))
        {
            var fromPos = board.FindPiecePosition(piece);
            if (fromPos == null) 
                continue;

            var legalMoves = _moveGen.GetLegalMoves(board, fromPos.Value);
            foreach (var toPos in legalMoves)
            {
                moves.Add((fromPos.Value, toPos));
            }
        }

        moves = moves.OrderByDescending(m => board.GetPiece(m.to) != null ? 1 : 0).ToList();

        return moves;
    }
}