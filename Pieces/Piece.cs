namespace ChessLib.Pieces;

public class Piece
{
    public PieceType Type { get; set; }
    public PieceColor Color { get; set; }

    public Piece(PieceType type, PieceColor color)
    {
        Type = type;
        Color = color;
    }
}