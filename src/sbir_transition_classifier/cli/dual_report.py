"""CLI command for generating dual-perspective SBIR transition reports."""

import time
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel

from ..analysis import analyze_transition_perspectives
from ..db.database import SessionLocal

@click.command()
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default=Path.cwd() / "reports",
    help='Output directory for reports'
)
@click.option(
    '--format', 'output_format',
    type=click.Choice(['console', 'json', 'csv']),
    default='console',
    help='Report output format'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def dual_report(output_dir: Path, output_format: str, verbose: bool):
    """Generate dual-perspective SBIR transition report (Company vs Award level)."""
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]📊 SBIR Dual-Perspective Report Generator[/bold blue]\n"
        "[dim]Company-Level vs Award-Level Success Analysis[/dim]",
        border_style="blue"
    ))
    
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate analysis
        perspectives = analyze_transition_perspectives(console=console)
        
        # Output based on format
        if output_format == 'console':
            # Already displayed by analyze_transition_perspectives
            pass
            
        elif output_format == 'json':
            import json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = output_dir / f"dual_perspective_report_{timestamp}.json"
            
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'company_metrics': {
                    'total_companies': perspectives.total_companies_with_sbir,
                    'companies_with_transitions': perspectives.companies_with_transitions,
                    'success_rate_percent': perspectives.company_transition_rate
                },
                'award_metrics': {
                    'total_awards': perspectives.total_sbir_awards,
                    'awards_with_transitions': perspectives.awards_with_transitions,
                    'success_rate_percent': perspectives.award_transition_rate
                },
                'cross_perspective': {
                    'avg_awards_per_transitioning_company': perspectives.avg_awards_per_transitioning_company,
                    'avg_transitions_per_successful_company': perspectives.avg_transitions_per_successful_company
                },
                'phase_breakdown': perspectives.awards_by_phase,
                'company_distribution': perspectives.companies_by_transition_count
            }
            
            with open(json_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            console.print(f"📄 JSON report saved: {json_file}")
            
        elif output_format == 'csv':
            import pandas as pd
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Summary metrics CSV
            summary_data = [
                ['Metric', 'Company_Level', 'Award_Level'],
                ['Total', perspectives.total_companies_with_sbir, perspectives.total_sbir_awards],
                ['With_Transitions', perspectives.companies_with_transitions, perspectives.awards_with_transitions],
                ['Success_Rate_Percent', perspectives.company_transition_rate, perspectives.award_transition_rate]
            ]
            
            summary_file = output_dir / f"dual_perspective_summary_{timestamp}.csv"
            pd.DataFrame(summary_data[1:], columns=summary_data[0]).to_csv(summary_file, index=False)
            
            # Phase breakdown CSV
            if perspectives.awards_by_phase:
                phase_data = []
                for phase, data in perspectives.awards_by_phase.items():
                    phase_data.append([phase, data['total'], data['transitioned'], data['rate']])
                
                phase_file = output_dir / f"phase_breakdown_{timestamp}.csv"
                pd.DataFrame(phase_data, columns=['Phase', 'Total_Awards', 'Transitioned', 'Success_Rate']).to_csv(phase_file, index=False)
                console.print(f"📊 Phase breakdown saved: {phase_file}")
            
            console.print(f"📄 Summary CSV saved: {summary_file}")
        
        processing_time = time.time() - start_time
        
        # Final summary
        console.print()
        console.print(Panel.fit(
            f"[bold green]✅ Report Generation Complete![/bold green]\n"
            f"[dim]Processing time: {processing_time:.1f}s[/dim]",
            border_style="green"
        ))
        
        # Key takeaways
        console.print("\n[bold yellow]🎯 Key Takeaways:[/bold yellow]")
        console.print(f"• {perspectives.company_transition_rate:.1f}% of SBIR companies achieve commercialization")
        console.print(f"• {perspectives.award_transition_rate:.1f}% of SBIR awards lead to follow-on contracts")
        
        if perspectives.award_transition_rate > perspectives.company_transition_rate:
            console.print("• Awards are more successful than companies at transitioning")
            console.print("• Focus on helping companies achieve sustained success")
        
    except Exception as e:
        console.print(f"[red]❌ Report generation failed: {e}[/red]")
        raise click.ClickException(str(e))
