using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public interface IMoveRule
{
    List<Position> GetMoves(Board board, Position pos, Piece piece);
}