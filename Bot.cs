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
            Piece? capturedPiece = game.Board.MakeMove(move.from, move.to);
            
            Piece? originalPiece = game.Board.GetPiece(move.to);
            bool isPromotion = false;
            if (originalPiece != null && originalPiece.Type == PieceType.Pawn && 
               ((originalPiece.Color == PieceColor.White && move.to.Y == 0) || 
                (originalPiece.Color == PieceColor.Black && move.to.Y == 7)))
            {
                isPromotion = true;
                game.Board.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, originalPiece.Color);
            }

            int score = Minimax(game.Board, _depth - 1, alpha, beta, nextTurn, game.PositionHistory);

            if (isPromotion)
            {
                game.Board.Grid[move.to.X, move.to.Y] = originalPiece;
            }
            game.Board.UndoMove(move.from, move.to, capturedPiece);

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
                Piece? capturedPiece = board.MakeMove(move.from, move.to);
                
                Piece? originalPiece = board.GetPiece(move.to);
                bool isPromotion = false;
                if (originalPiece != null && originalPiece.Type == PieceType.Pawn && move.to.Y == 0)
                {
                    isPromotion = true;
                    board.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, originalPiece.Color);
                }

                int score = Minimax(board, depth - 1, alpha, beta, nextTurn, gameHistory);

                if (isPromotion)
                {
                    board.Grid[move.to.X, move.to.Y] = originalPiece;
                }

                board.UndoMove(move.from, move.to, capturedPiece);

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
                Piece? capturedPiece = board.MakeMove(move.from, move.to);
                
                Piece? originalPiece = board.GetPiece(move.to);
                bool isPromotion = false;

                if (originalPiece != null && originalPiece.Type == PieceType.Pawn && move.to.Y == 7)
                {
                    isPromotion = true;
                    board.Grid[move.to.X, move.to.Y] = new Piece(PieceType.Queen, originalPiece.Color);
                }

                int score = Minimax(board, depth - 1, alpha, beta, nextTurn, gameHistory);

                if (isPromotion)
                {
                    board.Grid[move.to.X, move.to.Y] = originalPiece;
                }

                board.UndoMove(move.from, move.to, capturedPiece);

                minScore = Math.Min(minScore, score);
                beta = Math.Min(beta, score);
                
                if (beta <= alpha) break;
            }
            return minScore;
        }
    }
    

    private int GuessMoveScore(Board board, Position from, Position to)
    {
        int guess = 0;
        Piece? movingPiece = board.GetPiece(from);
        Piece? capturedPiece = board.GetPiece(to);

        if (capturedPiece != null && movingPiece != null)
        {
            int victimValue = GetPieceValue(capturedPiece.Type);
            int attackerValue = GetPieceValue(movingPiece.Type);
            
            guess = 10 * victimValue - attackerValue;
        }
        
        return guess;
    }

    private int GetPieceValue(PieceType type)
    {
        return type switch {
            PieceType.Pawn => 100,
            PieceType.Knight => 320,
            PieceType.Bishop => 330,
            PieceType.Rook => 500,
            PieceType.Queen => 900,
            PieceType.King => 20000,
            _ => 0
        };
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

        moves = moves.OrderByDescending(m => GuessMoveScore(board, m.from, m.to)).ToList();

        return moves;
    }
}