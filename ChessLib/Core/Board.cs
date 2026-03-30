using ChessLib.Pieces; 

namespace ChessLib.Core;

public class Board
{
    public Piece?[,] Grid = new Piece?[8,8];

    public Piece? GetPiece(Position pos)
    {
        if (pos.X < 0 || pos.X >= 8 || pos.Y < 0 || pos.Y >= 8) return null;
        return Grid[pos.X, pos.Y];
    }

    public Position? FindKing(PieceColor color)
    {
        for (int x = 0; x < 8; x++)
        {
            for (int y = 0; y < 8; y++)
            {
                var piece = Grid[x, y];
                if (piece != null && piece.Type == PieceType.King && piece.Color == color)
                {
                    return new Position(x, y);
                }
            }
        }
        return null;
    }

    public Position? FindPiecePosition(Piece piece)
    {
        for (int x = 0; x < 8; x++)
            for (int y = 0; y < 8; y++)
                if (Grid[x, y] == piece)
                    return new Position(x, y);
        return null;
    }

    public List<Piece> GetPiecesOfColor(PieceColor color)
    {
        var pieces = new List<Piece>();
        for (int x = 0; x < 8; x++)
        {
            for ( int y = 0; y < 8; y++)
            {
                var piece = Grid[x, y];
                if (piece != null && piece.Color == color)
                    pieces.Add(piece);
            }
        }

        return pieces;
    }

    public void Move(Position from, Position to)
    {
        Grid[to.X,to.Y] = Grid[from.X,from.Y];
        Grid[from.X,from.Y] = null;
    }

   public void SetupInitialPosition()
    {
        // очищаємо дошку
        Grid = new Piece?[8, 8];

        // Чорний ряд (основні фігури)
        Grid[0,0] = new Piece(PieceType.Rook, PieceColor.Black);
        Grid[1,0] = new Piece(PieceType.Knight, PieceColor.Black);
        Grid[2,0] = new Piece(PieceType.Bishop, PieceColor.Black);
        Grid[3,0] = new Piece(PieceType.Queen, PieceColor.Black);
        Grid[4,0] = new Piece(PieceType.King, PieceColor.Black);
        Grid[5,0] = new Piece(PieceType.Bishop, PieceColor.Black);
        Grid[6,0] = new Piece(PieceType.Knight, PieceColor.Black);
        Grid[7,0] = new Piece(PieceType.Rook, PieceColor.Black);

        // Чорний ряд пішаків
        for (int x = 0; x < 8; x++)
            Grid[x,1] = new Piece(PieceType.Pawn, PieceColor.Black);

        // Білий ряд (основні фігури)
        Grid[0,7] = new Piece(PieceType.Rook, PieceColor.White);
        Grid[1,7] = new Piece(PieceType.Knight, PieceColor.White);
        Grid[2,7] = new Piece(PieceType.Bishop, PieceColor.White);
        Grid[3,7] = new Piece(PieceType.Queen, PieceColor.White);
        Grid[4,7] = new Piece(PieceType.King, PieceColor.White);
        Grid[5,7] = new Piece(PieceType.Bishop, PieceColor.White);
        Grid[6,7] = new Piece(PieceType.Knight, PieceColor.White);
        Grid[7,7] = new Piece(PieceType.Rook, PieceColor.White);

        // Білий ряд пішаків
        for (int x = 0; x < 8; x++)
            Grid[x,6] = new Piece(PieceType.Pawn, PieceColor.White);
    }
}