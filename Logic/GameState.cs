using ChessLib.Core;

namespace ChessLib.Logic;

public class GameState
{
    public bool WhiteKingMoved = false;
    public bool BlackKingMoved = false;

    public bool WhiteLeftRookMoved = false;
    public bool WhiteRightRookMoved = false;

    public bool BlackLeftRookMoved = false;
    public bool BlackRightRookMoved = false;

    public Position? LastDoublePawnMove { get; set; } = null;
}