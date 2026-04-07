using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Reflection.Metadata;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using ChessLib.Core;
using ChessLib.Logic;
using ChessLib.Pieces;

namespace ChessAI;

public class Bot
{
    private PieceColor _botColor;
    private MoveGenerator _moveGen;
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

            int score = Minimax(copyBoard, _depth - 1, alpha, beta, nextTurn);

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

    //Minimax 
    private int Minimax(Board board, int depth, int alpha, int beta, PieceColor currentTurn)
    {
        if (depth == 0) 
            return Evaluator.Evaluate(board);

        var moves = GetAllMoves(board, currentTurn);

        if (moves.Count == 0) 
            return Evaluator.Evaluate(board);

        PieceColor nextTurn = currentTurn == PieceColor.White ? PieceColor.Black : PieceColor.White;

        if (currentTurn == PieceColor.White)
        {
            int maxScore = int.MinValue;
            foreach (var move in moves)
            {
                var copy = board.Clone();
                copy.Move(move.from, move.to);

                int score = Minimax(copy, depth -1, alpha, beta, nextTurn);
                maxScore = Math.Max(maxScore, score);

                alpha = Math.Max(alpha, score);
                if (beta <= alpha)
                {
                    break;
                }
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

                int score = Minimax(copy, depth -1, alpha, beta, nextTurn);
                minScore = Math.Min(minScore, score);

                beta = Math.Min(beta, score);
                if (beta <= alpha)
                {
                    break;
                }
            }
            return minScore;
        }
    }

    //collect all legal moves for current turn
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
        return moves;
    }
}