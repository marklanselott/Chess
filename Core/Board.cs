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

    public Board Clone()
    {
        var newBoard = new Board();

        for (int x = 0; x < 8; x++)
        {
            for (int y = 0; y < 8; y++)
            {
                var piece = Grid[x, y];
                if (piece != null)
                    newBoard.Grid[x, y] = new Piece(piece.Type, piece.Color);
            }
        }

        return newBoard;
    }

   public void SetupInitialPosition()
    {
        // clear board
        Grid = new Piece?[8, 8];

        // black pieces
        Grid[0,0] = new Piece(PieceType.Rook, PieceColor.Black);
        Grid[1,0] = new Piece(PieceType.Knight, PieceColor.Black);
        Grid[2,0] = new Piece(PieceType.Bishop, PieceColor.Black);
        Grid[3,0] = new Piece(PieceType.Queen, PieceColor.Black);
        Grid[4,0] = new Piece(PieceType.King, PieceColor.Black);
        Grid[5,0] = new Piece(PieceType.Bishop, PieceColor.Black);
        Grid[6,0] = new Piece(PieceType.Knight, PieceColor.Black);
        Grid[7,0] = new Piece(PieceType.Rook, PieceColor.Black);

        // black pawns
        for (int x = 0; x < 8; x++)
            Grid[x,1] = new Piece(PieceType.Pawn, PieceColor.Black);

        // white pieces
        Grid[0,7] = new Piece(PieceType.Rook, PieceColor.White);
        Grid[1,7] = new Piece(PieceType.Knight, PieceColor.White);
        Grid[2,7] = new Piece(PieceType.Bishop, PieceColor.White);
        Grid[3,7] = new Piece(PieceType.Queen, PieceColor.White);
        Grid[4,7] = new Piece(PieceType.King, PieceColor.White);
        Grid[5,7] = new Piece(PieceType.Bishop, PieceColor.White);
        Grid[6,7] = new Piece(PieceType.Knight, PieceColor.White);
        Grid[7,7] = new Piece(PieceType.Rook, PieceColor.White);

        // white pawns
        for (int x = 0; x < 8; x++)
            Grid[x,6] = new Piece(PieceType.Pawn, PieceColor.White);
    }

    //Export for Api
    public string ToAlgebraic(int x, int y)
    {
        char file = (char)('a' + x); 
        int rank = 8 - y;           
        return $"{file}{rank}";
    }

    public Dictionary<string, string> ExportBoardState()
    {
        var boardState = new Dictionary<string, string>();

        for (int x = 0; x < 8; x++)
        {
            for (int y = 0; y < 8; y++)
            {
                var piece = Grid[x, y];
                if (piece != null)
                {
                    string square = ToAlgebraic(x, y);
                    
                    boardState[square] = $"{piece.Color}{piece.Type}";
                }
            }
        }

        return boardState;
    }

    public string GetBoardString()
    {
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        for (int y = 0; y < 8; y++)
        {
            for (int x = 0; x < 8; x++)
            {
                var piece = Grid[x, y];
                if (piece == null) 
                    sb.Append(".");
                else 
                    sb.Append($"{(int)piece.Color}{(int)piece.Type}");
            }
        }
        return sb.ToString();
    }

    // collect all to fen
    public string GetFen(PieceColor currentTurn)
    {
        System.Text.StringBuilder fen = new System.Text.StringBuilder();

        for (int y = 0; y < 8; y++) 
        {
            int emptyCount = 0;
            for (int x = 0; x < 8; x++)
            {
                var piece = Grid[x, y];
                if (piece == null)
                {
                    emptyCount++;
                }
                else
                {
                    if (emptyCount > 0)
                    {
                        fen.Append(emptyCount);
                        emptyCount = 0;
                    }
                    fen.Append(GetPieceChar(piece));
                }
            }
            if (emptyCount > 0)
            {
                fen.Append(emptyCount);
            }
            
            if (y < 7) fen.Append('/');
        }

        fen.Append(currentTurn == PieceColor.White ? " w " : " b ");

        fen.Append("- - 0 1"); 

        return fen.ToString();
    }

    public void LoadFromFen(string fen)
    {
        Grid = new Piece[8, 8]; 
        
        string[] parts = fen.Split(' ');
        string[] rows = parts[0].Split('/'); 

        for (int y = 0; y < 8; y++)
        {
            int x = 0;
            foreach (char c in rows[y])
            {
                if (char.IsDigit(c))
                {
                    x += (int)char.GetNumericValue(c);
                }
                else
                {
                    Grid[x, y] = CreatePieceFromChar(c);
                    x++;
                }
            }
        }
    }

    private char GetPieceChar(Piece piece)
    {
        char c = piece.Type switch {
            PieceType.Pawn => 'p',
            PieceType.Knight => 'n',
            PieceType.Bishop => 'b',
            PieceType.Rook => 'r',
            PieceType.Queen => 'q',
            PieceType.King => 'k',
            _ => '?'
        };
        return piece.Color == PieceColor.White ? char.ToUpper(c) : c;
    }

    private Piece CreatePieceFromChar(char c)
    {
        PieceColor color = char.IsUpper(c) ? PieceColor.White : PieceColor.Black;
        PieceType type = char.ToLower(c) switch {
            'p' => PieceType.Pawn,
            'n' => PieceType.Knight,
            'b' => PieceType.Bishop,
            'r' => PieceType.Rook,
            'q' => PieceType.Queen,
            'k' => PieceType.King,
            _ => throw new Exception($"Inncorect char FEN: {c}")
        };
        return new Piece(type, color);
    }
}