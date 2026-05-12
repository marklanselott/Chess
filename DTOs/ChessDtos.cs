namespace ChessAPI.DTOs;

public class MoveRequest
{
    public string Fen { get; set; } = string.Empty;  
    public string From { get; set; } = string.Empty; 
    public string To { get; set; } = string.Empty;   
}

public class MoveResponse
{
    public bool IsLegal { get; set; }        
    public string? NewFen { get; set; }      
    public bool IsCheck { get; set; }
    public bool IsCheckmate { get; set; }    
    public bool IsDraw { get; set; }         
    public string? Message { get; set; }     
}


public class BotMoveRequest
{
    public string Fen { get; set; } = string.Empty;
    public int Depth { get; set; } = 3; 
}

public class BotMoveResponse
{
    public string NewFen { get; set; } = string.Empty;
    public string MoveFrom { get; set; } = string.Empty; 
    public string MoveTo { get; set; } = string.Empty;
    public bool IsCheck { get; set; }
    public bool IsCheckmate { get; set; }
}


public class AnalyzeRequest
{
    public List<string> HistoryFens { get; set; } = new List<string>();
}

public class MoveAnalysis
{
    public string Fen { get; set; } = string.Empty;
    public int Evaluation { get; set; } 
    public string BestMove { get; set; } = string.Empty; 
    public string Annotation { get; set; } = "Normal";
}

public class AnalysisJobResponse
{
    public string JobId { get; set; } = string.Empty;
    public string Status { get; set; } = "Processing"; 
    public List<MoveAnalysis>? Results { get; set; }
}


public class LegalMovesRequest
{
    public string Fen { get; set; } = string.Empty;
    public string From { get; set; } = string.Empty; 
}

public class LegalMovesResponse
{
    public List<string> LegalMoves { get; set; } = new(); 
    public string Message { get; set; } = string.Empty;
}