#!/usr/bin/env python3
"""
Script to run all integration tests for the list management functionality.
This script runs the complete test suite and generates a comprehensive report.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 5 minutes"
    except Exception as e:
        return False, "", str(e)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

def main():
    """Run all integration tests and generate report."""
    print("🚀 Starting Integration Test Suite for List Management")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get project root directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    project_root = backend_dir.parent
    frontend_dir = project_root / "frontend"
    
    print(f"Project root: {project_root}")
    print(f"Backend directory: {backend_dir}")
    print(f"Frontend directory: {frontend_dir}")
    
    # Test results tracking
    test_results = {
        'backend_unit': {'passed': False, 'output': '', 'error': ''},
        'backend_integration': {'passed': False, 'output': '', 'error': ''},
        'frontend_unit': {'passed': False, 'output': '', 'error': ''},
        'frontend_integration': {'passed': False, 'output': '', 'error': ''},
        'frontend_e2e': {'passed': False, 'output': '', 'error': ''}
    }
    
    # Backend Tests
    print_section("BACKEND TESTS")
    
    # Check if backend dependencies are available
    print_subsection("Checking Backend Dependencies")
    success, output, error = run_command("python -c 'import pytest, httpx, asgi_lifespan'", cwd=backend_dir)
    if not success:
        print("❌ Backend test dependencies not available")
        print(f"Error: {error}")
        print("Skipping backend tests...")
    else:
        print("✅ Backend test dependencies available")
        
        # Run backend unit tests
        print_subsection("Running Backend Unit Tests")
        success, output, error = run_command(
            "python -m pytest tests/test_kanban_list_model.py tests/test_kanban_list_service.py -v",
            cwd=backend_dir
        )
        test_results['backend_unit']['passed'] = success
        test_results['backend_unit']['output'] = output
        test_results['backend_unit']['error'] = error
        
        if success:
            print("✅ Backend unit tests passed")
        else:
            print("❌ Backend unit tests failed")
            print(f"Error: {error}")
        
        # Run backend integration tests
        print_subsection("Running Backend Integration Tests")
        success, output, error = run_command(
            "python -m pytest tests/test_integration_list_workflow.py -v",
            cwd=backend_dir
        )
        test_results['backend_integration']['passed'] = success
        test_results['backend_integration']['output'] = output
        test_results['backend_integration']['error'] = error
        
        if success:
            print("✅ Backend integration tests passed")
        else:
            print("❌ Backend integration tests failed")
            print(f"Error: {error}")
    
    # Frontend Tests
    print_section("FRONTEND TESTS")
    
    # Check if frontend dependencies are available
    print_subsection("Checking Frontend Dependencies")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        print("Skipping frontend tests...")
    else:
        success, output, error = run_command("pnpm --version", cwd=frontend_dir)
        if not success:
            print("❌ pnpm not available, trying npm...")
            success, output, error = run_command("npm --version", cwd=frontend_dir)
            package_manager = "npm"
        else:
            package_manager = "pnpm"
        
        if not success:
            print("❌ No package manager available")
            print("Skipping frontend tests...")
        else:
            print(f"✅ Using {package_manager} as package manager")
            
            # Check if node_modules exists
            if not (frontend_dir / "node_modules").exists():
                print("📦 Installing frontend dependencies...")
                success, output, error = run_command(f"{package_manager} install", cwd=frontend_dir)
                if not success:
                    print("❌ Failed to install frontend dependencies")
                    print(f"Error: {error}")
                else:
                    print("✅ Frontend dependencies installed")
            
            # Run frontend unit tests
            print_subsection("Running Frontend Unit Tests")
            success, output, error = run_command(
                f"{package_manager} vitest src/services/__tests__ src/components --run",
                cwd=frontend_dir
            )
            test_results['frontend_unit']['passed'] = success
            test_results['frontend_unit']['output'] = output
            test_results['frontend_unit']['error'] = error
            
            if success:
                print("✅ Frontend unit tests passed")
            else:
                print("❌ Frontend unit tests failed")
                print(f"Error: {error}")
            
            # Run frontend integration tests
            print_subsection("Running Frontend Integration Tests")
            success, output, error = run_command(
                f"{package_manager} vitest src/test/integration-workflow.test.ts --run",
                cwd=frontend_dir
            )
            test_results['frontend_integration']['passed'] = success
            test_results['frontend_integration']['output'] = output
            test_results['frontend_integration']['error'] = error
            
            if success:
                print("✅ Frontend integration tests passed")
            else:
                print("❌ Frontend integration tests failed")
                print(f"Error: {error}")
            
            # Run frontend E2E tests
            print_subsection("Running Frontend E2E Tests")
            success, output, error = run_command(
                f"{package_manager} vitest src/test/e2e-workflow.test.ts --run",
                cwd=frontend_dir
            )
            test_results['frontend_e2e']['passed'] = success
            test_results['frontend_e2e']['output'] = output
            test_results['frontend_e2e']['error'] = error
            
            if success:
                print("✅ Frontend E2E tests passed")
            else:
                print("❌ Frontend E2E tests failed")
                print(f"Error: {error}")
    
    # Generate Test Report
    print_section("TEST RESULTS SUMMARY")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result['passed'])
    
    print(f"Total test suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests / total_tests) * 100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Generate detailed report file
    report_file = project_root / "integration_test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Integration Test Report\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Success Rate:** {(passed_tests / total_tests) * 100:.1f}% ({passed_tests}/{total_tests})\n\n")
        
        f.write("## Summary\n\n")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            f.write(f"- **{test_name}**: {status}\n")
        
        f.write("\n## Detailed Results\n\n")
        for test_name, result in test_results.items():
            f.write(f"### {test_name}\n\n")
            f.write(f"**Status:** {'PASS' if result['passed'] else 'FAIL'}\n\n")
            
            if result['output']:
                f.write("**Output:**\n```\n")
                f.write(result['output'])
                f.write("\n```\n\n")
            
            if result['error']:
                f.write("**Error:**\n```\n")
                f.write(result['error'])
                f.write("\n```\n\n")
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if passed_tests == total_tests:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()