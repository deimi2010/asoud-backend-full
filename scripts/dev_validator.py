#!/usr/bin/env python3
"""
ASOUD Development Environment - Comprehensive Testing & Validation
Complete validation suite for development environment
"""

import asyncio
import aiohttp
import docker
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple
import psutil

class DevelopmentValidator:
    """Comprehensive development environment validator"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.base_url = "http://localhost"
        self.results = {
            'docker': [],
            'services': [],
            'network': [],
            'security': [],
            'performance': [],
            'database': [],
            'redis': [],
            'files': [],
            'summary': {}
        }
        
    def log_result(self, category: str, test: str, status: bool, message: str = "", details: Dict = None):
        """Log validation result"""
        result = {
            'test': test,
            'status': 'PASS' if status else 'FAIL',
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.results[category].append(result)
        
        # Print real-time feedback
        icon = "✅" if status else "❌"
        print(f"{icon} {test}: {message}")
        
    async def validate_docker_services(self):
        """Validate Docker services and containers"""
        print("\n🐳 Validating Docker Services...")
        
        # Check if Docker is running
        try:
            self.docker_client.ping()
            self.log_result('docker', 'Docker Daemon', True, "Docker daemon is running")
        except Exception as e:
            self.log_result('docker', 'Docker Daemon', False, f"Docker daemon error: {e}")
            return
        
        # Check required containers
        required_containers = [
            "asoud_api_dev",
            "asoud_db_dev", 
            "asoud_redis_dev",
            "asoud_nginx_dev",
            "asoud_adminer_dev",
            "asoud_redis_commander_dev",
            "asoud_mailhog_dev"
        ]
        
        for container_name in required_containers:
            try:
                container = self.docker_client.containers.get(container_name)
                is_running = container.status == 'running'
                self.log_result(
                    'docker', 
                    f'Container {container_name}', 
                    is_running,
                    f"Status: {container.status}",
                    {'container_id': container.id, 'image': container.image.tags}
                )
            except docker.errors.NotFound:
                self.log_result('docker', f'Container {container_name}', False, "Container not found")
            except Exception as e:
                self.log_result('docker', f'Container {container_name}', False, f"Error: {e}")
        
        # Check network
        try:
            network = self.docker_client.networks.get("asoud_dev_network")
            containers_in_network = len(network.containers)
            self.log_result(
                'docker', 
                'Development Network', 
                containers_in_network > 0,
                f"Network exists with {containers_in_network} containers",
                {'network_id': network.id}
            )
        except docker.errors.NotFound:
            self.log_result('docker', 'Development Network', False, "Network not found")
        
        # Check volumes
        volumes = ['asoud_dev_db_data', 'asoud_dev_redis_data', 'asoud_dev_static_volume', 'asoud_dev_media_volume']
        for volume_name in volumes:
            try:
                volume = self.docker_client.volumes.get(volume_name)
                self.log_result('docker', f'Volume {volume_name}', True, "Volume exists")
            except docker.errors.NotFound:
                self.log_result('docker', f'Volume {volume_name}', False, "Volume not found")
    
    async def validate_service_endpoints(self):
        """Validate service endpoints and health"""
        print("\n🌐 Validating Service Endpoints...")
        
        endpoints = [
            ('/', 'Main Application'),
            ('/health/', 'Health Check'),
            ('/api/', 'API Root'),
            ('/api/v1/health/', 'API Health'),
            ('/admin/', 'Django Admin'),
            ('/adminer/', 'Database Admin'),
            ('/redis/', 'Redis Commander'),
            ('/mail/', 'MailHog Interface'),
            ('/static/admin/css/base.css', 'Static Files'),
            ('/nginx-status', 'Nginx Status')
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for endpoint, name in endpoints:
                try:
                    start_time = time.time()
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        is_healthy = response.status < 400
                        self.log_result(
                            'services',
                            name,
                            is_healthy,
                            f"Status: {response.status}, Response: {response_time:.1f}ms",
                            {
                                'status_code': response.status,
                                'response_time_ms': response_time,
                                'headers': dict(response.headers)
                            }
                        )
                except asyncio.TimeoutError:
                    self.log_result('services', name, False, "Request timeout")
                except Exception as e:
                    self.log_result('services', name, False, f"Error: {e}")
    
    async def validate_api_functionality(self):
        """Validate API functionality"""
        print("\n🔌 Validating API Functionality...")
        
        api_tests = [
            ('/api/v1/', 'GET', 'API Root Endpoint'),
            ('/api/v1/auth/pin/create/', 'POST', 'PIN Creation', {'mobile_number': '09123456789'}),
            ('/api/v1/users/banks/', 'GET', 'Banks List'),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, method, name, data in [(t[0], t[1], t[2], t[3] if len(t) > 3 else None) for t in api_tests]:
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            result = await response.json()
                    else:
                        async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                            result = await response.json()
                    
                    is_success = response.status < 400
                    self.log_result(
                        'services',
                        f'API {name}',
                        is_success,
                        f"Status: {response.status}",
                        {'response': result}
                    )
                except Exception as e:
                    self.log_result('services', f'API {name}', False, f"Error: {e}")
    
    def validate_network_connectivity(self):
        """Validate network connectivity between services"""
        print("\n🔗 Validating Network Connectivity...")
        
        network_tests = [
            ('asoud_api_dev', 'asoud_db_dev', 5432),
            ('asoud_api_dev', 'asoud_redis_dev', 6379),
            ('asoud_nginx_dev', 'asoud_api_dev', 8000),
        ]
        
        for source, target, port in network_tests:
            try:
                result = subprocess.run([
                    'docker', 'exec', source, 
                    'nc', '-z', target, str(port)
                ], capture_output=True, text=True, timeout=10)
                
                is_connected = result.returncode == 0
                self.log_result(
                    'network',
                    f'{source} -> {target}:{port}',
                    is_connected,
                    "Connected" if is_connected else "Connection failed"
                )
            except subprocess.TimeoutExpired:
                self.log_result('network', f'{source} -> {target}:{port}', False, "Connection timeout")
            except Exception as e:
                self.log_result('network', f'{source} -> {target}:{port}', False, f"Error: {e}")
    
    def validate_security_configuration(self):
        """Validate security configuration"""
        print("\n🔒 Validating Security Configuration...")
        
        # Check SSL certificates
        ssl_cert_path = "data/nginx/ssl/dev.crt"
        ssl_key_path = "data/nginx/ssl/dev.key"
        
        cert_exists = os.path.exists(ssl_cert_path)
        key_exists = os.path.exists(ssl_key_path)
        
        self.log_result('security', 'SSL Certificate', cert_exists, 
                       "Certificate exists" if cert_exists else "Certificate missing")
        self.log_result('security', 'SSL Private Key', key_exists,
                       "Private key exists" if key_exists else "Private key missing")
        
        # Check .env file
        env_exists = os.path.exists('.env')
        self.log_result('security', 'Environment File', env_exists,
                       ".env file exists" if env_exists else ".env file missing")
        
        if env_exists:
            # Check for required environment variables
            required_vars = [
                'DJANGO_SECRET_KEY',
                'DATABASE_PASSWORD', 
                'REDIS_PASSWORD'
            ]
            
            with open('.env', 'r') as f:
                env_content = f.read()
            
            for var in required_vars:
                var_present = var in env_content
                self.log_result('security', f'Env Var {var}', var_present,
                               "Variable set" if var_present else "Variable missing")
        
        # Check file permissions
        sensitive_paths = ['logs/', 'data/', '.env']
        for path in sensitive_paths:
            if os.path.exists(path):
                stat = os.stat(path)
                permissions = oct(stat.st_mode)[-3:]
                is_secure = permissions != '777'  # Not world-writable
                self.log_result('security', f'Permissions {path}', is_secure,
                               f"Permissions: {permissions}")
    
    def validate_performance_metrics(self):
        """Validate performance metrics"""
        print("\n⚡ Validating Performance Metrics...")
        
        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        self.log_result('performance', 'CPU Usage', cpu_percent < 80,
                       f"CPU: {cpu_percent:.1f}%")
        self.log_result('performance', 'Memory Usage', memory_percent < 85,
                       f"Memory: {memory_percent:.1f}%")
        self.log_result('performance', 'Disk Usage', disk_percent < 90,
                       f"Disk: {disk_percent:.1f}%")
        
        # Check container resource usage
        for container_name in ['asoud_api_dev', 'asoud_db_dev', 'asoud_redis_dev']:
            try:
                container = self.docker_client.containers.get(container_name)
                stats = container.stats(stream=False)
                
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100
                
                self.log_result('performance', f'{container_name} Memory', memory_percent < 80,
                               f"Memory: {memory_percent:.1f}%")
            except Exception as e:
                self.log_result('performance', f'{container_name} Stats', False, f"Error: {e}")
    
    def validate_database_connection(self):
        """Validate database connection and functionality"""
        print("\n🗄️ Validating Database...")
        
        # Test database connection
        try:
            result = subprocess.run([
                'docker', 'exec', 'asoud_api_dev',
                'python', 'manage.py', 'check', '--database', 'default'
            ], capture_output=True, text=True, timeout=30)
            
            is_connected = result.returncode == 0
            self.log_result('database', 'Connection', is_connected,
                           "Connected" if is_connected else f"Error: {result.stderr}")
        except Exception as e:
            self.log_result('database', 'Connection', False, f"Error: {e}")
        
        # Test migrations
        try:
            result = subprocess.run([
                'docker', 'exec', 'asoud_api_dev',
                'python', 'manage.py', 'showmigrations', '--plan'
            ], capture_output=True, text=True, timeout=30)
            
            has_unapplied = '[X]' not in result.stdout and '[ ]' in result.stdout
            self.log_result('database', 'Migrations', not has_unapplied,
                           "All migrations applied" if not has_unapplied else "Unapplied migrations found")
        except Exception as e:
            self.log_result('database', 'Migrations', False, f"Error: {e}")
    
    def validate_redis_connection(self):
        """Validate Redis connection and functionality"""
        print("\n🔴 Validating Redis...")
        
        # Test Redis connection
        try:
            result = subprocess.run([
                'docker', 'exec', 'asoud_redis_dev',
                'redis-cli', '-a', 'redis_dev_pass', 'ping'
            ], capture_output=True, text=True, timeout=10)
            
            is_connected = 'PONG' in result.stdout
            self.log_result('redis', 'Connection', is_connected,
                           "Connected" if is_connected else "Connection failed")
        except Exception as e:
            self.log_result('redis', 'Connection', False, f"Error: {e}")
        
        # Test Redis functionality
        try:
            # Set a test key
            subprocess.run([
                'docker', 'exec', 'asoud_redis_dev',
                'redis-cli', '-a', 'redis_dev_pass', 'set', 'test_key', 'test_value'
            ], capture_output=True, text=True, timeout=10)
            
            # Get the test key
            result = subprocess.run([
                'docker', 'exec', 'asoud_redis_dev',
                'redis-cli', '-a', 'redis_dev_pass', 'get', 'test_key'
            ], capture_output=True, text=True, timeout=10)
            
            is_working = 'test_value' in result.stdout
            self.log_result('redis', 'Functionality', is_working,
                           "Read/Write working" if is_working else "Read/Write failed")
        except Exception as e:
            self.log_result('redis', 'Functionality', False, f"Error: {e}")
    
    def validate_file_structure(self):
        """Validate file structure and permissions"""
        print("\n📁 Validating File Structure...")
        
        required_files = [
            'docker-compose.dev-complete.yaml',
            'nginx/nginx-dev.conf',
            'redis/redis-dev.conf',
            'scripts/init-db.sql',
            'scripts/dev-setup.sh',
            'scripts/dev_monitor.py',
            'DEVELOPMENT_SECURITY_GUIDE.md'
        ]
        
        required_dirs = [
            'logs/',
            'data/',
            'nginx/',
            'redis/',
            'scripts/'
        ]
        
        for file_path in required_files:
            exists = os.path.exists(file_path)
            self.log_result('files', f'File {file_path}', exists,
                           "Exists" if exists else "Missing")
        
        for dir_path in required_dirs:
            exists = os.path.exists(dir_path)
            self.log_result('files', f'Directory {dir_path}', exists,
                           "Exists" if exists else "Missing")
    
    def generate_summary(self):
        """Generate validation summary"""
        print("\n📊 Generating Summary...")
        
        summary = {}
        for category, tests in self.results.items():
            if category == 'summary':
                continue
                
            total = len(tests)
            passed = len([t for t in tests if t['status'] == 'PASS'])
            failed = total - passed
            
            summary[category] = {
                'total': total,
                'passed': passed,
                'failed': failed,
                'success_rate': (passed / total * 100) if total > 0 else 0
            }
        
        self.results['summary'] = summary
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 VALIDATION SUMMARY")
        print("="*60)
        
        overall_passed = sum(s['passed'] for s in summary.values())
        overall_total = sum(s['total'] for s in summary.values())
        overall_rate = (overall_passed / overall_total * 100) if overall_total > 0 else 0
        
        for category, stats in summary.items():
            status_icon = "✅" if stats['success_rate'] == 100 else "⚠️" if stats['success_rate'] > 80 else "❌"
            print(f"{status_icon} {category.upper()}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        
        print("-" * 60)
        overall_icon = "✅" if overall_rate == 100 else "⚠️" if overall_rate > 80 else "❌"
        print(f"{overall_icon} OVERALL: {overall_passed}/{overall_total} ({overall_rate:.1f}%)")
        
        if overall_rate == 100:
            print("\n🎉 Development environment is fully validated and ready!")
        elif overall_rate > 80:
            print("\n⚠️  Development environment is mostly ready with minor issues")
        else:
            print("\n❌ Development environment has significant issues requiring attention")
    
    def save_report(self, filename: str = None):
        """Save validation report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dev_validation_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Validation report saved to: {filename}")
    
    async def run_full_validation(self):
        """Run complete validation suite"""
        print("🔍 ASOUD Development Environment Validation")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all validations
        await self.validate_docker_services()
        await self.validate_service_endpoints()
        await self.validate_api_functionality()
        self.validate_network_connectivity()
        self.validate_security_configuration()
        self.validate_performance_metrics()
        self.validate_database_connection()
        self.validate_redis_connection()
        self.validate_file_structure()
        
        # Generate summary
        self.generate_summary()
        
        # Save report
        self.save_report()
        
        end_time = time.time()
        print(f"\n⏱️  Validation completed in {end_time - start_time:.1f} seconds")

async def main():
    """Main function"""
    validator = DevelopmentValidator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "docker":
            await validator.validate_docker_services()
        elif command == "services":
            await validator.validate_service_endpoints()
        elif command == "api":
            await validator.validate_api_functionality()
        elif command == "network":
            validator.validate_network_connectivity()
        elif command == "security":
            validator.validate_security_configuration()
        elif command == "performance":
            validator.validate_performance_metrics()
        elif command == "database":
            validator.validate_database_connection()
        elif command == "redis":
            validator.validate_redis_connection()
        elif command == "files":
            validator.validate_file_structure()
        elif command == "full":
            await validator.run_full_validation()
        elif command == "help":
            print("ASOUD Development Validator")
            print("")
            print("Usage:")
            print("  python dev_validator.py [command]")
            print("")
            print("Commands:")
            print("  full        - Run complete validation (default)")
            print("  docker      - Validate Docker services")
            print("  services    - Validate service endpoints")
            print("  api         - Validate API functionality")
            print("  network     - Validate network connectivity")
            print("  security    - Validate security configuration")
            print("  performance - Validate performance metrics")
            print("  database    - Validate database connection")
            print("  redis       - Validate Redis connection")
            print("  files       - Validate file structure")
            print("  help        - Show this help")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python dev_validator.py help' for available commands")
    else:
        # Default: run full validation
        await validator.run_full_validation()

if __name__ == "__main__":
    asyncio.run(main())