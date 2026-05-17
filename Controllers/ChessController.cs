using Microsoft.AspNetCore.Mvc;
using System.Collections.Concurrent;
using System.Threading.Tasks;
using System;
using System.Collections.Generic;
using ChessAPI.DTOs;
using ChessLib.Core;
using ChessLib.Logic;
using ChessLib.Pieces;
using ChessAI; 

namespace ChessAPI.Controllers;

[Route("api/[controller]")]
[ApiController]
public class ChessController : ControllerBase
{
    [HttpPost("move")]
    public IActionResult MakeMove([FromBody] MoveRequest request)
    {
        try
        {
            string[] fenParts = request.Fen.Split(' ');
            PieceColor currentTurn = fenParts[1] == "w" ? PieceColor.White : PieceColor.Black;

            Board board = new Board();
            board.LoadFromFen(request.Fen);
            
            GameManager game = new GameManager(board, currentTurn);

            if (request.From.Length != 2 || request.To.Length != 2) 
                return BadRequest(new MoveResponse { IsLegal = false, Message = "Incorrect format." });

            int fromX = char.ToLower(request.From[0]) - 'a';
            int fromY = 8 - (int)char.GetNumericValue(request.From[1]);
            
            int toX = char.ToLower(request.To[0]) - 'a';
            int toY = 8 - (int)char.GetNumericValue(request.To[1]);

            Position fromPos = new Position(fromX, fromY);
            Position toPos = new Position(toX, toY);

            bool isLegal = game.MakeMove(fromPos, toPos, out var promotionOptions);

            if (!isLegal)
            {
                return Ok(new MoveResponse { IsLegal = false, Message = "Illegal move." });
            }

            PieceColor nextTurn = currentTurn == PieceColor.White ? PieceColor.Black : PieceColor.White;

            return Ok(new MoveResponse
            {
                IsLegal = true,
                NewFen = game.Board.GetFen(nextTurn),
                IsCheck = game.IsCheck,
                IsCheckmate = game.IsCheckmate,
                IsDraw = game.IsStalemate,
                Message = "Succes move"
            });
        }
        catch (Exception ex)
        {
            return BadRequest(new MoveResponse { IsLegal = false, Message = $"Error: {ex.Message}" });
        }
    }


    [HttpPost("legal-moves")]
    public IActionResult GetLegalMoves([FromBody] LegalMovesRequest request)
    {
        try
        {
            if (request.From.Length != 2)
                return BadRequest(new LegalMovesResponse { Message = "Неправильний формат." });

            string[] fenParts = request.Fen.Split(' ');
            PieceColor currentTurn = fenParts[1] == "w" ? PieceColor.White : PieceColor.Black;

            Board board = new Board();
            board.LoadFromFen(request.Fen);
            GameManager game = new GameManager(board, currentTurn);

            int fromX = char.ToLower(request.From[0]) - 'a';
            int fromY = 8 - (int)char.GetNumericValue(request.From[1]);
            Position fromPos = new Position(fromX, fromY);

            var legalMoves = game.GetLegalMoves(fromPos);

            List<string> resultMoves = new List<string>();
            foreach (var pos in legalMoves)
            {
                string squareStr = $"{(char)('a' + pos.X)}{8 - pos.Y}";
                resultMoves.Add(squareStr);
            }

            return Ok(new LegalMovesResponse
            {
                LegalMoves = resultMoves,
                Message = "Успіх"
            });
        }
        catch (Exception ex)
        {
            return BadRequest(new LegalMovesResponse { Message = $"Помилка: {ex.Message}" });
        }
    }


    [HttpPost("bot-move")]
    public IActionResult MakeBotMove([FromBody] BotMoveRequest request)
    {
        try
        {
            string[] fenParts = request.Fen.Split(' ');
            PieceColor botColor = fenParts[1] == "w" ? PieceColor.White : PieceColor.Black;
            
            Board board = new Board();
            board.LoadFromFen(request.Fen);
            GameManager game = new GameManager(board, botColor);

            Bot aiBot = new Bot(botColor, request.Depth); 

            var bestMove = aiBot.FindBestMove(game);

            game.MakeMove(bestMove.from, bestMove.to, out _);

            string fromStr = $"{(char)('a' + bestMove.from.X)}{8 - bestMove.from.Y}";
            string toStr = $"{(char)('a' + bestMove.to.X)}{8 - bestMove.to.Y}";

            PieceColor nextTurn = botColor == PieceColor.White ? PieceColor.Black : PieceColor.White;
            
            return Ok(new BotMoveResponse
            {
                NewFen = game.Board.GetFen(nextTurn),
                MoveFrom = fromStr,
                MoveTo = toStr,
                IsCheck = game.IsCheck,
                IsCheckmate = game.IsCheckmate
            });
        }
        catch (Exception ex)
        {
            return BadRequest($"AI error: {ex.Message}");
        }
    }


    private static readonly ConcurrentDictionary<string, AnalysisJobResponse> _analysisJobs = new();

   [HttpPost("analyze/start")]
    public IActionResult StartAnalysis([FromBody] AnalyzeRequest request)
    {
        string jobId = Guid.NewGuid().ToString();
        _analysisJobs[jobId] = new AnalysisJobResponse { JobId = jobId, Status = "Processing" };
        
        Task.Run(() => RunHeavyAnalysis(jobId, request.HistoryFens, request.Depth));
        
        return Accepted(new { JobId = jobId, Message = "Start analizing" });
    }

    [HttpGet("analyze/status/{jobId}")]
    public IActionResult GetAnalysisStatus(string jobId)
    {
        if (_analysisJobs.TryGetValue(jobId, out var job))
        {
            if (job.Status == "Completed" || job.Status == "Error")
            {
                _analysisJobs.TryRemove(jobId, out _);
            }
            return Ok(job);
        }
        return NotFound(new { Message = "Task not found" });
    }

    private void RunHeavyAnalysis(string jobId, List<string> historyFens, int depth)
    {
        try
        {
            List<MoveAnalysis> results = new List<MoveAnalysis>();
            int previousEval = 0;

            for (int i = 0; i < historyFens.Count - 1; i++)
            {
                string currentFen = historyFens[i];
                Board board = new Board();
                board.LoadFromFen(currentFen);
                
                string[] fenParts = currentFen.Split(' ');
                PieceColor currentTurn = fenParts[1] == "w" ?
                PieceColor.White : PieceColor.Black;

                GameManager game = new GameManager(board, currentTurn);

                Bot aiBot = new Bot(currentTurn, depth); 
                var bestMove = aiBot.FindBestMove(game);
                
                int currentScore = Evaluator.Evaluate(game.Board);
                string annotation = "Normal";
                
                string fromStr = $"{(char)('a' + bestMove.from.X)}{8 - bestMove.from.Y}";
                string toStr = $"{(char)('a' + bestMove.to.X)}{8 - bestMove.to.Y}";

                if (i > 0)
                {
                    int delta = currentScore - previousEval;
                    
                    if (currentTurn == PieceColor.Black) delta = -delta;

                    if (delta <= -300) annotation = "Blunder";     
                    else if (delta <= -100) annotation = "Mistake"; 
                    else if (delta <= -50) annotation = "Inaccuracy";
                    else if (delta >= 200) annotation = "Great";    
                }

                previousEval = currentScore;

                results.Add(new MoveAnalysis 
                {
                    Fen = currentFen,
                    Evaluation = currentScore, 
                    BestMove = fromStr + toStr, 
                    Annotation = annotation
                });
            }

            if (_analysisJobs.TryGetValue(jobId, out var jobInfo))
            {
                jobInfo.Status = "Completed";
                jobInfo.Results = results;
            }
        }
        catch (Exception) 
        {
            if (_analysisJobs.TryGetValue(jobId, out var jobInfo))
            {
                jobInfo.Status = "Error";
            }
        }
    }
}