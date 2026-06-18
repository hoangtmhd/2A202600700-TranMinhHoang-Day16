#!/usr/bin/env python3
"""
Script chạy thử nghiệm nhanh (demo) ReAct vs Reflexion Agent trên file golden test set (hotpot_150.json).
Mặc định chạy với 3 mẫu đầu tiên để tiết kiệm thời gian và chi phí API.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

# Cấu hình stdout/stderr sang UTF-8 trên Windows để tránh lỗi UnicodeEncodeError khi in tiếng Việt
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Thêm thư mục cha vào sys.path để import được src.reflexion_lab
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from dotenv import load_dotenv
load_dotenv(parent_dir / ".env")

import typer
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.utils import load_dataset

app = typer.Typer(add_completion=False)

@app.command()
def main(
    dataset: str = typer.Option(
        "data/hotpot_150.json", 
        help="Đường dẫn đến file golden test set"
    ),
    num_samples: int = typer.Option(
        3, 
        help="Số lượng mẫu chạy thử (mặc định = 3 để chạy nhanh)"
    ),
    reflexion_attempts: int = typer.Option(
        3, 
        help="Số lần thử tối đa cho Reflexion Agent"
    )
) -> None:
    console = Console()
    dataset_path = parent_dir / dataset
    
    # 1. Kiểm tra API Key và Dataset
    if not os.getenv("GEMINI_API_KEY"):
        console.print("[red bold]Lỗi: Không tìm thấy GEMINI_API_KEY trong file .env hoặc biến môi trường![/red bold]")
        console.print("Vui lòng tạo hoặc điền API key vào file .env ở thư mục gốc.")
        raise typer.Exit(code=1)
        
    if not dataset_path.exists():
        console.print(f"[red bold]Lỗi: Không tìm thấy file dữ liệu tại {dataset_path}[/red bold]")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"[bold green]Khởi chạy Demo so sánh ReAct vs Reflexion Agent[/bold green]\n"
        f"- Dataset: {dataset}\n"
        f"- Số mẫu chạy thử: {num_samples} / 150\n"
        f"- Reflexion Max Attempts: {reflexion_attempts}",
        title="Agent Demo System"
    ))

    # 2. Load dữ liệu và khởi tạo Agents
    examples = load_dataset(str(dataset_path))[:num_samples]
    react_agent = ReActAgent()
    reflexion_agent = ReflexionAgent(max_attempts=reflexion_attempts)

    results = []

    # 3. Chạy thử nghiệm
    with console.status("[bold blue]Đang xử lý các câu hỏi với ReAct và Reflexion...") as status:
        for idx, example in enumerate(examples, 1):
            console.log(f"[yellow]Đang chạy câu hỏi {idx}/{num_samples}...[/yellow]")
            
            # Chạy ReAct Agent
            t0 = time.time()
            react_res = react_agent.run(example)
            react_time = time.time() - t0
            
            # Chạy Reflexion Agent
            t1 = time.time()
            reflexion_res = reflexion_agent.run(example)
            reflexion_time = time.time() - t1

            results.append({
                "idx": idx,
                "question": example.question,
                "gold": example.gold_answer,
                "react": react_res,
                "react_time": react_time,
                "reflexion": reflexion_res,
                "reflexion_time": reflexion_time
            })

    # 4. Hiển thị kết quả chi tiết
    console.print("\n[bold cyan]=== CHI TIẾT KẾT QUẢ TỪNG CÂU HỎI ===[/bold cyan]\n")
    for r in results:
        q_panel = Panel(
            f"[bold]Câu hỏi:[/] {r['question']}\n"
            f"[bold green]Đáp án chuẩn (Gold):[/] {r['gold']}\n\n"
            f"[bold blue]● ReAct Agent:[/]\n"
            f"  - Trả lời: {r['react'].predicted_answer}\n"
            f"  - Khớp đáp án (EM): {'[green]Đúng (1)[/]' if r['react'].is_correct else '[red]Sai (0)[/]'}\n"
            f"  - Token sử dụng: {r['react'].token_estimate}\n"
            f"  - Thời gian chạy: {r['react_time']:.2f}s\n\n"
            f"[bold purple]● Reflexion Agent:[/]\n"
            f"  - Trả lời: {r['reflexion'].predicted_answer}\n"
            f"  - Khớp đáp án (EM): {'[green]Đúng (1)[/]' if r['reflexion'].is_correct else '[red]Sai (0)[/]'}\n"
            f"  - Số lần thử thực tế: {r['reflexion'].attempts}\n"
            f"  - Token sử dụng: {r['reflexion'].token_estimate}\n"
            f"  - Thời gian chạy: {r['reflexion_time']:.2f}s",
            title=f"Mẫu số {r['idx']}",
            border_style="cyan"
        )
        console.print(q_panel)
        console.print()

    # 5. Hiển thị bảng tổng hợp so sánh
    table = Table(title="Bảng so sánh tổng hợp hiệu năng Demo", show_header=True, header_style="bold magenta")
    table.add_column("Chỉ số", style="dim")
    table.add_column("ReAct Agent", justify="center")
    table.add_column("Reflexion Agent", justify="center")

    total_react_em = sum(1 for r in results if r["react"].is_correct)
    total_reflexion_em = sum(1 for r in results if r["reflexion"].is_correct)
    avg_react_tokens = sum(r["react"].token_estimate for r in results) / num_samples
    avg_reflexion_tokens = sum(r["reflexion"].token_estimate for r in results) / num_samples
    avg_react_latency = sum(r["react_time"] for r in results) / num_samples
    avg_reflexion_latency = sum(r["reflexion_time"] for r in results) / num_samples

    table.add_row("Tỉ lệ Đúng (Exact Match)", f"{total_react_em}/{num_samples} ({total_react_em/num_samples:.1%})", f"{total_reflexion_em}/{num_samples} ({total_reflexion_em/num_samples:.1%})")
    table.add_row("Token trung bình", f"{avg_react_tokens:.1f}", f"{avg_reflexion_tokens:.1f}")
    table.add_row("Thời gian chạy trung bình", f"{avg_react_latency:.2f}s", f"{avg_reflexion_latency:.2f}s")
    
    console.print(table)
    console.print("\n[bold green]✓ Đã hoàn thành chạy thử nghiệm![/bold green] Bạn có thể chạy lại với nhiều mẫu hơn bằng tuỳ chọn `--num-samples <số_mẫu>`")

if __name__ == "__main__":
    app()
