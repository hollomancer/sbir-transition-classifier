"""Transition statistics and analysis."""

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
class TransitionStatistics:
    """Comprehensive transition detection statistics."""
    total_detections: int = 0
    by_fiscal_year: Dict[int, int] = None
    by_agency: Dict[str, int] = None
    by_detection_type: Dict[str, int] = None
    by_confidence_level: Dict[str, int] = None
    cross_agency_transitions: int = 0
    same_agency_transitions: int = 0
    top_vendors: List[Tuple[str, int]] = None
    avg_confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.by_fiscal_year is None:
            self.by_fiscal_year = {}
        if self.by_agency is None:
            self.by_agency = {}
        if self.by_detection_type is None:
            self.by_detection_type = {}
        if self.by_confidence_level is None:
            self.by_confidence_level = {}
        if self.top_vendors is None:
            self.top_vendors = []

def generate_transition_overview(console: Console = None) -> TransitionStatistics:
    """Generate comprehensive transition statistics overview."""
    if console is None:
        console = Console()
    
    console.print("\n[bold blue]📊 Generating Transition Statistics Overview...[/bold blue]")
    
    db = SessionLocal()
    stats = TransitionStatistics()
    
    try:
        # Total detections
        stats.total_detections = db.query(models.Detection).count()
        
        # By fiscal year (extract from contract start dates)
        fy_query = text("""
            SELECT 
                CASE 
                    WHEN strftime('%m', c.start_date) >= '10' 
                    THEN CAST(strftime('%Y', c.start_date) AS INTEGER) + 1
                    ELSE CAST(strftime('%Y', c.start_date) AS INTEGER)
                END as fiscal_year,
                COUNT(*) as count 
            FROM detections d
            JOIN contracts c ON d.contract_id = c.id
            WHERE c.start_date IS NOT NULL 
            GROUP BY fiscal_year 
            ORDER BY fiscal_year DESC
            LIMIT 10
        """)
        stats.by_fiscal_year = dict(db.execute(fy_query).fetchall())
        
        # By agency (from contracts)
        agency_query = text("""
            SELECT c.agency, COUNT(*) as count 
            FROM detections d
            JOIN contracts c ON d.contract_id = c.id
            GROUP BY c.agency 
            ORDER BY count DESC 
            LIMIT 10
        """)
        stats.by_agency = dict(db.execute(agency_query).fetchall())
        
        # Cross-agency vs same-agency analysis
        cross_agency_query = text("""
            SELECT 
                CASE 
                    WHEN sa.agency != c.agency THEN 'cross_agency'
                    ELSE 'same_agency'
                END as transition_type,
                COUNT(*) as count
            FROM detections d
            JOIN sbir_awards sa ON d.sbir_award_id = sa.id
            JOIN contracts c ON d.contract_id = c.id
            GROUP BY transition_type
        """)
        
        for transition_type, count in db.execute(cross_agency_query).fetchall():
            if transition_type == 'cross_agency':
                stats.cross_agency_transitions = count
            else:
                stats.same_agency_transitions = count
        
        # Average confidence score (using likelihood_score)
        avg_score_query = text("SELECT AVG(likelihood_score) FROM detections WHERE likelihood_score IS NOT NULL")
        result = db.execute(avg_score_query).fetchone()
        stats.avg_confidence_score = float(result[0]) if result[0] else 0.0
        
        # Top vendors by detection count
        vendor_query = text("""
            SELECT v.name, COUNT(d.id) as detection_count
            FROM vendors v
            JOIN sbir_awards sa ON v.id = sa.vendor_id
            JOIN detections d ON sa.id = d.sbir_award_id
            GROUP BY v.id, v.name
            ORDER BY detection_count DESC
            LIMIT 10
        """)
        stats.top_vendors = list(db.execute(vendor_query).fetchall())
        
        # Confidence level distribution (using likelihood_score and confidence)
        confidence_query = text("""
            SELECT 
                CASE 
                    WHEN confidence = 'high' THEN 'High Confidence'
                    WHEN confidence = 'medium' THEN 'Medium Confidence'
                    WHEN confidence = 'low' THEN 'Low Confidence'
                    ELSE 'Unknown'
                END as confidence_level,
                COUNT(*) as count
            FROM detections
            WHERE confidence IS NOT NULL
            GROUP BY confidence_level
            ORDER BY 
                CASE confidence 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                    ELSE 4 
                END
        """)
        stats.by_confidence_level = dict(db.execute(confidence_query).fetchall())
        
    finally:
        db.close()
    
    # Display statistics
    _display_statistics(stats, console)
    
    return stats

def _display_statistics(stats: TransitionStatistics, console: Console):
    """Display formatted transition statistics."""
    
    # Overview panel
    console.print()
    console.print(Panel.fit(
        f"[bold green]📈 Transition Detection Overview[/bold green]\n"
        f"[dim]Total Detections: {stats.total_detections:,}[/dim]",
        border_style="green"
    ))
    
    # Summary table
    summary_table = Table(title="🎯 Key Metrics")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right", style="green")
    summary_table.add_column("Percentage", justify="right", style="yellow")
    
    total = stats.total_detections
    cross_pct = (stats.cross_agency_transitions / total * 100) if total > 0 else 0
    same_pct = (stats.same_agency_transitions / total * 100) if total > 0 else 0
    
    summary_table.add_row("Total Detections", f"{total:,}", "100.0%")
    summary_table.add_row("Cross-Agency Transitions", f"{stats.cross_agency_transitions:,}", f"{cross_pct:.1f}%")
    summary_table.add_row("Same-Agency Transitions", f"{stats.same_agency_transitions:,}", f"{same_pct:.1f}%")
    summary_table.add_row("Average Confidence", f"{stats.avg_confidence_score:.3f}", "")
    
    console.print(summary_table)
    
    # Top agencies
    if stats.by_agency:
        agency_table = Table(title="🏛️ Top Agencies by Detections")
        agency_table.add_column("Agency", style="cyan")
        agency_table.add_column("Detections", justify="right", style="green")
        agency_table.add_column("Share", justify="right", style="yellow")
        
        for agency, count in list(stats.by_agency.items())[:5]:
            pct = (count / total * 100) if total > 0 else 0
            agency_table.add_row(agency[:40], f"{count:,}", f"{pct:.1f}%")
        
        console.print(agency_table)
    
    # Fiscal year distribution
    if stats.by_fiscal_year:
        fy_table = Table(title="📅 Detections by Fiscal Year")
        fy_table.add_column("Fiscal Year", style="cyan")
        fy_table.add_column("Detections", justify="right", style="green")
        fy_table.add_column("Share", justify="right", style="yellow")
        
        for fy, count in sorted(stats.by_fiscal_year.items(), reverse=True)[:5]:
            pct = (count / total * 100) if total > 0 else 0
            fy_table.add_row(str(fy), f"{count:,}", f"{pct:.1f}%")
        
        console.print(fy_table)
    
    # Confidence distribution
    if stats.by_confidence_level:
        conf_table = Table(title="🎯 Confidence Level Distribution")
        conf_table.add_column("Confidence Level", style="cyan")
        conf_table.add_column("Detections", justify="right", style="green")
        conf_table.add_column("Share", justify="right", style="yellow")
        
        for level, count in stats.by_confidence_level.items():
            pct = (count / total * 100) if total > 0 else 0
            conf_table.add_row(level, f"{count:,}", f"{pct:.1f}%")
        
        console.print(conf_table)
    
    # Top vendors
    if stats.top_vendors:
        vendor_table = Table(title="🏢 Top Vendors by Detections")
        vendor_table.add_column("Vendor", style="cyan")
        vendor_table.add_column("Detections", justify="right", style="green")
        
        for vendor, count in stats.top_vendors[:5]:
            vendor_table.add_row(vendor[:50], f"{count:,}")
        
        console.print(vendor_table)
