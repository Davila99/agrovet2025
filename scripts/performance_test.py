"""
Script para ejecutar pruebas de rendimiento reales y obtener métricas.
Ejecuta pruebas básicas contra los servicios y genera un reporte.
"""
import requests
import time
import statistics
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Configuración
BASE_URL = os.getenv('BASE_URL', 'http://localhost')
SERVICES = {
    'auth': f'{BASE_URL}:8002',
    'media': f'{BASE_URL}:8001',
    'profiles': f'{BASE_URL}:8003',
    'marketplace': f'{BASE_URL}:8004',
    'foro': f'{BASE_URL}:8005',
    'chat': f'{BASE_URL}:8006',
}

RESULTS = {
    'timestamp': datetime.now().isoformat(),
    'services': {}
}


def test_endpoint(service_name, endpoint, method='GET', data=None, headers=None):
    """Probar un endpoint y retornar métricas."""
    url = f"{SERVICES.get(service_name, '')}{endpoint}"
    latencies = []
    errors = 0
    success = 0
    
    try:
        start = time.time()
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            return None
        
        latency = (time.time() - start) * 1000  # en ms
        latencies.append(latency)
        
        if response.status_code < 400:
            success += 1
        else:
            errors += 1
            
    except requests.exceptions.RequestException as e:
        errors += 1
        return {
            'endpoint': endpoint,
            'status': 'error',
            'error': str(e),
            'latency_ms': None
        }
    
    if latencies:
        return {
            'endpoint': endpoint,
            'status': 'success' if success > 0 else 'error',
            'latency_ms': statistics.mean(latencies),
            'latency_p50': statistics.median(latencies) if len(latencies) > 1 else latencies[0],
            'success_count': success,
            'error_count': errors,
            'status_code': response.status_code
        }
    return None


def test_concurrent_requests(service_name, endpoint, num_requests=10, num_threads=5):
    """Probar requests concurrentes."""
    latencies = []
    errors = 0
    success = 0
    
    def make_request():
        url = f"{SERVICES.get(service_name, '')}{endpoint}"
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            if response.status_code < 400:
                success += 1
                return True
            else:
                errors += 1
                return False
        except Exception as e:
            errors += 1
            return False
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        for future in as_completed(futures):
            future.result()
    
    total_time = time.time() - start_time
    rps = num_requests / total_time if total_time > 0 else 0
    
    if latencies:
        return {
            'total_requests': num_requests,
            'success_count': success,
            'error_count': errors,
            'total_time_sec': total_time,
            'rps': rps,
            'latency_avg_ms': statistics.mean(latencies),
            'latency_p50_ms': statistics.median(latencies),
            'latency_p95_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0],
            'latency_p99_ms': statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0],
            'latency_min_ms': min(latencies),
            'latency_max_ms': max(latencies),
        }
    return None


def check_service_health(service_name):
    """Verificar si un servicio está disponible."""
    health_url = f"{SERVICES.get(service_name, '')}/health/"
    try:
        response = requests.get(health_url, timeout=2)
        return response.status_code == 200
    except:
        return False


def main():
    print("=" * 60)
    print("PRUEBAS DE RENDIMIENTO - AGROVET2025")
    print("=" * 60)
    print(f"Timestamp: {RESULTS['timestamp']}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Verificar servicios disponibles
    print("Verificando servicios disponibles...")
    available_services = {}
    for service_name, service_url in SERVICES.items():
        is_available = check_service_health(service_name)
        available_services[service_name] = is_available
        status = "[OK] Disponible" if is_available else "[X] No disponible"
        print(f"  {service_name:15} {status:20} ({service_url})")
    
    print()
    
    if not any(available_services.values()):
        print("[!] No hay servicios disponibles para probar.")
        print("   Inicia los servicios con: docker-compose -f docker-compose.dev.yml up")
        return
    
    # Pruebas básicas
    print("Ejecutando pruebas básicas...")
    print()
    
    test_cases = [
        ('auth', '/health/', 'GET'),
        ('media', '/health/', 'GET'),
        ('profiles', '/health/', 'GET'),
        ('marketplace', '/health/', 'GET'),
        ('foro', '/health/', 'GET'),
        ('chat', '/health/', 'GET'),
    ]
    
    for service_name, endpoint, method in test_cases:
        if not available_services.get(service_name):
            continue
            
        print(f"Probando {service_name:15} {endpoint}...", end=' ')
        result = test_endpoint(service_name, endpoint, method)
        if result:
            if result['status'] == 'success':
                print(f"[OK] {result['latency_ms']:.2f}ms")
                if service_name not in RESULTS['services']:
                    RESULTS['services'][service_name] = {}
                RESULTS['services'][service_name]['health'] = result
            else:
                print(f"[ERROR] {result.get('error', 'Unknown')}")
        else:
            print("[ERROR] No response")
    
    print()
    
    # Pruebas de carga concurrente
    print("Ejecutando pruebas de carga concurrente...")
    print()
    
    load_tests = [
        ('auth', '/health/', 20, 5),
        ('profiles', '/health/', 20, 5),
        ('marketplace', '/health/', 20, 5),
    ]
    
    for service_name, endpoint, num_requests, num_threads in load_tests:
        if not available_services.get(service_name):
            continue
            
        print(f"Prueba de carga: {service_name:15} ({num_requests} requests, {num_threads} threads)...", end=' ')
        result = test_concurrent_requests(service_name, endpoint, num_requests, num_threads)
        if result:
            print(f"[OK] {result['rps']:.2f} RPS, P95: {result['latency_p95_ms']:.2f}ms")
            if service_name not in RESULTS['services']:
                RESULTS['services'][service_name] = {}
            RESULTS['services'][service_name]['load_test'] = result
        else:
            print("[ERROR]")
    
    print()
    
    # Guardar resultados
    output_file = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    
    print(f"[OK] Resultados guardados en: {output_file}")
    print()
    
    # Resumen
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for service_name, data in RESULTS['services'].items():
        print(f"\n{service_name.upper()}:")
        if 'health' in data:
            h = data['health']
            print(f"  Health Check: {h['latency_ms']:.2f}ms")
        if 'load_test' in data:
            lt = data['load_test']
            print(f"  Load Test:")
            print(f"    RPS: {lt['rps']:.2f}")
            print(f"    Latency P50: {lt['latency_p50_ms']:.2f}ms")
            print(f"    Latency P95: {lt['latency_p95_ms']:.2f}ms")
            print(f"    Success Rate: {(lt['success_count']/lt['total_requests']*100):.1f}%")
    
    print()


if __name__ == '__main__':
    main()

