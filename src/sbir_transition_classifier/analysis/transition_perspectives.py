"""Dual-perspective transition analytics: Company vs Award level."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..db.database import SessionLocal
from ..core import models

@dataclass
class TransitionPerspectives:
    """Analytics for both company-level and award-level transitions."""
    
    # Company-level metrics
    total_companies_with_sbir: int = 0
    companies_with_transitions: int = 0
    company_transition_rate: float = 0.0
    
    # Award-level metrics  
    total_sbir_awards: int = 0
    awards_with_transitions: int = 0
    award_transition_rate: float = 0.0
    
    # Cross-perspective analysis
    avg_awards_per_transitioning_company: float = 0.0
    avg_transitions_per_successful_company: float = 0.0
    
    # Detailed breakdowns
    companies_by_transition_count: Dict[int, int] = None
    awards_by_phase: Dict[str, Dict[str, int]] = None

def analyze_transition_perspectives(console: Console = None) -> TransitionPerspectives:
    """Analyze transitions from both company and award perspectives."""
    if console is None:
        console = Console()
    
    console.print("\n[bold blue]📊 Dual-Perspective Transition Analysis[/bold blue]")
    
    db = SessionLocal()
    perspectives = TransitionPerspectives()
    
    try:
        # Company-level analysis
        company_query = text("""
            SELECT 
                COUNT(DISTINCT v.id) as total_companies,
                COUNT(DISTINCT CASE WHEN d.id IS NOT NULL THEN v.id END) as companies_with_transitions
            FROM vendors v
            JOIN sbir_awards sa ON v.id = sa.vendor_id
            LEFT JOIN detections d ON sa.id = d.sbir_award_id
        """)
        
        company_result = db.execute(company_query).fetchone()
        perspectives.total_companies_with_sbir = company_result[0]
        perspectives.companies_with_transitions = company_result[1]
        perspectives.company_transition_rate = (
            perspectives.companies_with_transitions / perspectives.total_companies_with_sbir * 100
            if perspectives.total_companies_with_sbir > 0 else 0
        )
        
        # Award-level analysis
        award_query = text("""
            SELECT 
                COUNT(sa.id) as total_awards,
                COUNT(d.id) as awards_with_transitions
            FROM sbir_awards sa
            LEFT JOIN detections d ON sa.id = d.sbir_award_id
        """)
        
        award_result = db.execute(award_query).fetchone()
        perspectives.total_sbir_awards = award_result[0]
        perspectives.awards_with_transitions = award_result[1]
        perspectives.award_transition_rate = (
            perspectives.awards_with_transitions / perspectives.total_sbir_awards * 100
            if perspectives.total_sbir_awards > 0 else 0
        )
        
        # Cross-perspective metrics
        if perspectives.companies_with_transitions > 0:
            # Average awards per transitioning company
            avg_awards_query = text("""
                SELECT AVG(award_count) FROM (
                    SELECT v.id, COUNT(sa.id) as award_count
                    FROM vendors v
                    JOIN sbir_awards sa ON v.id = sa.vendor_id
                    JOIN detections d ON sa.id = d.sbir_award_id
                    GROUP BY v.id
                )
            """)
            avg_awards_result = db.execute(avg_awards_query).fetchone()
            perspectives.avg_awards_per_transitioning_company = float(avg_awards_result[0] or 0)
            
            # Average transitions per successful company
            avg_transitions_query = text("""
                SELECT AVG(transition_count) FROM (
                    SELECT v.id, COUNT(d.id) as transition_count
                    FROM vendors v
                    JOIN sbir_awards sa ON v.id = sa.vendor_id
                    JOIN detections d ON sa.id = d.sbir_award_id
                    GROUP BY v.id
                )
            """)
            avg_transitions_result = db.execute(avg_transitions_query).fetchone()
            perspectives.avg_transitions_per_successful_company = float(avg_transitions_result[0] or 0)
        
        # Company transition count distribution
        company_dist_query = text("""
            SELECT 
                transition_count,
                COUNT(*) as company_count
            FROM (
                SELECT v.id, COUNT(d.id) as transition_count
                FROM vendors v
                JOIN sbir_awards sa ON v.id = sa.vendor_id
                LEFT JOIN detections d ON sa.id = d.sbir_award_id
                GROUP BY v.id
            )
            GROUP BY transition_count
            ORDER BY transition_count
        """)
        
        perspectives.companies_by_transition_count = dict(db.execute(company_dist_query).fetchall())
        
        # Award phase analysis
        phase_query = text("""
            SELECT 
                sa.phase,
                COUNT(sa.id) as total_awards,
                COUNT(d.id) as transitioned_awards
            FROM sbir_awards sa
            LEFT JOIN detections d ON sa.id = d.sbir_award_id
            WHERE sa.phase IS NOT NULL AND sa.phase != ''
            GROUP BY sa.phase
            ORDER BY sa.phase
        """)
        
        perspectives.awards_by_phase = {}
        for phase, total, transitioned in db.execute(phase_query).fetchall():
            perspectives.awards_by_phase[phase] = {
                'total': total,
                'transitioned': transitioned,
                'rate': (transitioned / total * 100) if total > 0 else 0
            }
        
    finally:
        db.close()
    
    # Display results
    _display_perspectives(perspectives, console)
    
    return perspectives

def _display_perspectives(perspectives: TransitionPerspectives, console: Console):
    """Display dual-perspective transition analytics."""
    
    # Header
    console.print()
    console.print(Panel.fit(
        "[bold green]📈 Transition Success Analysis[/bold green]\n"
        "[dim]Company-Level vs Award-Level Perspectives[/dim]",
        border_style="green"
    ))
    
    # Main comparison table
    comparison_table = Table(title="🎯 Company vs Award Transition Rates")
    comparison_table.add_column("Perspective", style="cyan")
    comparison_table.add_column("Total", justify="right", style="blue")
    comparison_table.add_column("With Transitions", justify="right", style="green")
    comparison_table.add_column("Success Rate", justify="right", style="yellow")
    
    comparison_table.add_row(
        "🏢 Companies",
        f"{perspectives.total_companies_with_sbir:,}",
        f"{perspectives.companies_with_transitions:,}",
        f"{perspectives.company_transition_rate:.1f}%"
    )
    
    comparison_table.add_row(
        "🏆 SBIR Awards", 
        f"{perspectives.total_sbir_awards:,}",
        f"{perspectives.awards_with_transitions:,}",
        f"{perspectives.award_transition_rate:.1f}%"
    )
    
    console.print(comparison_table)
    
    # Cross-perspective insights
    if perspectives.companies_with_transitions > 0:
        insights_table = Table(title="🔍 Cross-Perspective Insights")
        insights_table.add_column("Metric", style="cyan")
        insights_table.add_column("Value", justify="right", style="green")
        
        insights_table.add_row(
            "Avg SBIR awards per transitioning company",
            f"{perspectives.avg_awards_per_transitioning_company:.1f}"
        )
        insights_table.add_row(
            "Avg transitions per successful company",
            f"{perspectives.avg_transitions_per_successful_company:.1f}"
        )
        
        console.print(insights_table)
    
    # Company transition distribution
    if perspectives.companies_by_transition_count:
        dist_table = Table(title="🏢 Company Transition Distribution")
        dist_table.add_column("Transitions", style="cyan")
        dist_table.add_column("Companies", justify="right", style="green")
        dist_table.add_column("Percentage", justify="right", style="yellow")
        
        total_companies = sum(perspectives.companies_by_transition_count.values())
        for transitions, count in sorted(perspectives.companies_by_transition_count.items()):
            pct = (count / total_companies * 100) if total_companies > 0 else 0
            if transitions == 0:
                dist_table.add_row(f"❌ {transitions}", f"{count:,}", f"{pct:.1f}%")
            elif transitions <= 5:
                dist_table.add_row(f"✅ {transitions}", f"{count:,}", f"{pct:.1f}%")
            else:
                dist_table.add_row(f"🌟 {transitions}+", f"{count:,}", f"{pct:.1f}%")
        
        console.print(dist_table)
    
    # Phase-level analysis
    if perspectives.awards_by_phase:
        phase_table = Table(title="🏆 Award Transition Rates by Phase")
        phase_table.add_column("Phase", style="cyan")
        phase_table.add_column("Total Awards", justify="right", style="blue")
        phase_table.add_column("Transitioned", justify="right", style="green")
        phase_table.add_column("Success Rate", justify="right", style="yellow")
        
        for phase, data in perspectives.awards_by_phase.items():
            phase_table.add_row(
                phase,
                f"{data['total']:,}",
                f"{data['transitioned']:,}",
                f"{data['rate']:.1f}%"
            )
        
        console.print(phase_table)
    
    # Key insights
    console.print()
    console.print("[bold yellow]💡 Key Insights:[/bold yellow]")
    
    if perspectives.company_transition_rate > perspectives.award_transition_rate:
        console.print("• Companies are more likely to transition than individual awards")
        console.print("• Successful companies often have multiple transitioning awards")
    else:
        console.print("• Individual awards have higher transition rates than companies")
        console.print("• Most successful companies transition only one award")
    
    console.print(f"• {perspectives.company_transition_rate:.1f}% of SBIR companies successfully commercialize")
    console.print(f"• {perspectives.award_transition_rate:.1f}% of SBIR awards lead to follow-on contracts")
