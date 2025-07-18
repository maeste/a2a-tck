#!/usr/bin/env python3
"""
Main script for A2A specification change tracking and analysis.
"""

import argparse
import logging
import sys
import json
from pathlib import Path

# Add current directory to Python path for local imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spec_tracker.spec_downloader import SpecDownloader
from spec_tracker.spec_parser import SpecParser
from spec_tracker.spec_comparator import SpecComparator
from spec_tracker.test_impact_analyzer import TestImpactAnalyzer
from spec_tracker.report_generator import ReportGenerator

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def build_github_urls(branch_or_tag: str = "main") -> tuple[str, str]:
    """Build GitHub raw URLs for the specified branch or tag."""
    base_url = f"https://raw.githubusercontent.com/a2aproject/A2A/{branch_or_tag}"
    json_url = f"{base_url}/specification/json/a2a.json"
    md_url = f"{base_url}/docs/specification.md"
    return json_url, md_url

def main():
    """Main entry point for spec change tracker."""
    parser = argparse.ArgumentParser(
        description="Track A2A specification changes and analyze test impacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Check for changes with defaults (main branch)
  %(prog)s --branch "v1.2.0"                 # Check against specific tag/branch
  %(prog)s --output report.md                 # Save to custom file
  %(prog)s --verbose                          # Enable detailed logging
  %(prog)s --json-export results.json        # Export JSON data
  %(prog)s --summary-only                     # Generate summary report only
        """
    )
    parser.add_argument(
        '--branch',
        '--ref',
        dest='branch',
        help='GitHub branch or tag to compare against (e.g., "main", "v1.2.0", "dev"). Defaults to main.'
    )
    parser.add_argument(
        '--json-url',
        help='URL for JSON schema (overrides --branch if specified)'
    )
    parser.add_argument(
        '--md-url', 
        help='URL for Markdown spec (overrides --branch if specified)'
    )
    parser.add_argument(
        '--output',
        help='Output file for report (default: reports/spec_analysis_report.md)',
        default='reports/spec_analysis_report.md'
    )
    parser.add_argument(
        '--json-export',
        help='Export analysis results as JSON to specified file'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Generate only a concise summary report'
    )
    parser.add_argument(
        '--current-md',
        help='Path to current markdown spec file (default: current_spec/A2A_SPECIFICATION.md)',
        default='current_spec/A2A_SPECIFICATION.md'
    )
    parser.add_argument(
        '--current-json',
        help='Path to current JSON schema file (default: current_spec/a2a_schema.json)',
        default='current_spec/a2a_schema.json'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform analysis without saving reports'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Starting A2A Specification Change Analysis")
        
        # Determine URLs to use
        if args.json_url and args.md_url:
            # Custom URLs provided
            json_url = args.json_url
            md_url = args.md_url
            source_ref = "custom URLs"
        elif args.branch:
            # Branch/tag specified
            json_url, md_url = build_github_urls(args.branch)
            source_ref = args.branch
            logger.info(f"📍 Comparing against branch/tag: {args.branch}")
        else:
            # Default to main branch
            json_url, md_url = build_github_urls("main")
            source_ref = "main"
        
        # Step 1: Download latest specs
        logger.info(f"📥 Downloading specifications from {source_ref}...")
        if args.verbose:
            logger.info(f"📄 JSON URL: {json_url}")
            logger.info(f"📄 MD URL: {md_url}")
        
        downloader = SpecDownloader()
        
        try:
            new_json, new_md = downloader.download_spec(json_url, md_url)
            logger.info(f"✅ Downloaded specifications: {len(new_json)} JSON definitions, {len(new_md)} chars markdown")
        except Exception as e:
            logger.error(f"❌ Failed to download specifications: {e}")
            logger.info("💡 Check your internet connection and URLs")
            return 1
        
        # Step 2: Parse specifications
        logger.info("🔍 Parsing specifications...")
        spec_parser = SpecParser()
        
        # Parse current specs
        try:
            if not Path(args.current_md).exists():
                logger.error(f"❌ Current markdown spec not found: {args.current_md}")
                return 1
            if not Path(args.current_json).exists():
                logger.error(f"❌ Current JSON schema not found: {args.current_json}")
                return 1
                
            with open(args.current_md, 'r', encoding='utf-8') as f:
                current_md = f.read()
            with open(args.current_json, 'r', encoding='utf-8') as f:
                current_json = json.load(f)
                
            current_spec = {
                'markdown': spec_parser.parse_markdown(current_md),
                'json': spec_parser.parse_json_schema(current_json)
            }
            
            new_spec = {
                'markdown': spec_parser.parse_markdown(new_md),
                'json': spec_parser.parse_json_schema(new_json)
            }
            
            logger.info(f"✅ Parsed current spec: {len(current_spec['markdown']['requirements'])} requirements, {len(current_spec['json']['definitions'])} definitions")
            logger.info(f"✅ Parsed new spec: {len(new_spec['markdown']['requirements'])} requirements, {len(new_spec['json']['definitions'])} definitions")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse specifications: {e}")
            return 1
        
        # Step 3: Compare specifications
        logger.info("📊 Comparing specifications...")
        comparator = SpecComparator()
        
        try:
            spec_changes = comparator.compare_specs(current_spec, new_spec)
            total_changes = spec_changes.get('summary', {}).get('total_changes', 0)
            
            if total_changes == 0:
                logger.info("✅ No specification changes detected")
            else:
                logger.info(f"📋 Detected {total_changes} specification changes")
                
                # Log change summary
                impact_summary = spec_changes.get('summary', {})
                req_changes = impact_summary.get('requirement_changes', {})
                if req_changes.get('added', 0) > 0 or req_changes.get('removed', 0) > 0:
                    logger.info(f"  Requirements: +{req_changes.get('added', 0)}, -{req_changes.get('removed', 0)}, ~{req_changes.get('modified', 0)}")
                
                breaking_changes = len(spec_changes.get('impact_classification', {}).get('breaking_changes', []))
                if breaking_changes > 0:
                    logger.warning(f"⚠️  {breaking_changes} breaking changes detected!")
                    
        except Exception as e:
            logger.error(f"❌ Failed to compare specifications: {e}")
            return 1
        
        # Step 4: Analyze test impacts
        logger.info("🧪 Analyzing test impacts...")
        analyzer = TestImpactAnalyzer()
        
        try:
            test_impacts = analyzer.analyze_impact(spec_changes)
            coverage_analysis = analyzer.analyze_coverage(current_spec['markdown']['requirements'])
            
            total_impacted = sum(len(test_list) for test_list in test_impacts.values())
            logger.info(f"✅ Impact analysis complete: {total_impacted} tests potentially affected")
            
            # Log impact summary
            for impact_type, test_list in test_impacts.items():
                if len(test_list) > 0:
                    logger.info(f"  {impact_type}: {len(test_list)} tests")
                    
            # Log coverage summary
            overall_coverage = coverage_analysis.get('overall_coverage', {})
            req_coverage = overall_coverage.get('requirement_coverage_percentage', 0)
            test_doc = overall_coverage.get('test_documentation_percentage', 0)
            logger.info(f"📊 Current coverage: {req_coverage:.1f}% requirements, {test_doc:.1f}% test documentation")
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze test impacts: {e}")
            return 1
        
        # Step 5: Generate report
        logger.info("📝 Generating report...")
        generator = ReportGenerator()
        
        try:
            if args.summary_only:
                report = generator.generate_summary_report(
                    spec_changes,
                    test_impacts,
                    coverage_analysis
                )
                report_type = "summary"
            else:
                report = generator.generate_report(
                    spec_changes,
                    test_impacts,
                    coverage_analysis,
                    "Current A2A Specification",
                    "Latest A2A Specification"
                )
                report_type = "detailed"
                
            if not args.dry_run:
                output_file = Path(args.output)
                # Create parent directory if it doesn't exist
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                logger.info(f"✅ Successfully generated {report_type} report: {args.output}")

                if args.json_export:
                    json_output_file = Path(args.json_export)
                    # Create parent directory if it doesn't exist
                    json_output_file.parent.mkdir(parents=True, exist_ok=True)
                    export_data = {
                        "spec_changes": spec_changes,
                        "test_impacts": test_impacts,
                        "coverage_analysis": coverage_analysis
                    }
                    with open(json_output_file, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2)
                    logger.info(f"✅ Successfully exported JSON data to: {args.json_export}")
            else:
                logger.info("ξη Dry run complete, no reports were saved.")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")
            return 1
        
        # Step 6: Summary and recommendations
        logger.info("🎯 Analysis Summary:")
        
        total_changes = spec_changes.get('summary', {}).get('total_changes', 0)
        breaking_changes = len(spec_changes.get('impact_classification', {}).get('breaking_changes', []))
        total_impacted = sum(len(test_list) for test_list in test_impacts.values())
        
        if breaking_changes > 0:
            logger.warning(f"🚨 CRITICAL: {breaking_changes} breaking changes require immediate attention")
            logger.warning("   Review all breaking changes before deploying")
            logger.warning("   Update affected tests and client code")
        elif total_impacted > 20:
            logger.warning(f"⚠️  HIGH PRIORITY: {total_impacted} tests affected - review required")
            logger.info("   Review affected tests and update as needed")
        elif total_changes > 0:
            logger.info(f"📋 MEDIUM PRIORITY: {total_changes} changes detected - update recommended")
            logger.info("   Consider updating tests for new requirements")
        else:
            logger.info("✅ LOW PRIORITY: No changes detected - routine maintenance only")
        
        if not args.dry_run:
            logger.info(f"📖 Full analysis available in: {args.output}")
        
        logger.info("🎉 A2A Specification Change Analysis completed successfully!")
        
        # Return appropriate exit code
        if breaking_changes > 0:
            return 2  # Breaking changes detected
        elif total_changes > 0:
            return 1  # Changes detected
        else:
            return 0  # No changes
        
    except KeyboardInterrupt:
        logger.info("🛑 Analysis interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 