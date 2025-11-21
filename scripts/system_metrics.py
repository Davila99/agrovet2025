"""
Script para obtener métricas del sistema (CPU, RAM, etc.)
"""
import psutil
import json
from datetime import datetime
import os

def get_system_metrics():
    """Obtener métricas del sistema."""
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'per_cpu': psutil.cpu_percent(interval=1, percpu=True)
        },
        'memory': {
            'total_gb': psutil.virtual_memory().total / (1024**3),
            'available_gb': psutil.virtual_memory().available / (1024**3),
            'used_gb': psutil.virtual_memory().used / (1024**3),
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total_gb': psutil.disk_usage('/').total / (1024**3),
            'used_gb': psutil.disk_usage('/').used / (1024**3),
            'free_gb': psutil.disk_usage('/').free / (1024**3),
            'percent': psutil.disk_usage('/').percent
        }
    }
    return metrics

def main():
    try:
        metrics = get_system_metrics()
        print("Métricas del Sistema:")
        print(json.dumps(metrics, indent=2))
        
        output_file = f"system_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n[OK] Metricas guardadas en: {output_file}")
    except ImportError:
        print("[!] psutil no esta instalado. Instala con: pip install psutil")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == '__main__':
    main()

