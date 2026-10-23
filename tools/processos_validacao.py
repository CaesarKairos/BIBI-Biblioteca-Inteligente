"""Encerra somente a árvore do processo iniciado por um roteiro de validação."""
import psutil


def stop_process_tree(process):
    try:
        parent=psutil.Process(process.pid)
        children=parent.children(recursive=True)
    except psutil.NoSuchProcess:
        process.wait(timeout=15)
        return
    targets=list(reversed(children))+[parent]
    for target in targets:
        try:target.terminate()
        except psutil.NoSuchProcess:pass
    _,alive=psutil.wait_procs(targets,timeout=10)
    for target in alive:
        try:target.kill()
        except psutil.NoSuchProcess:pass
    psutil.wait_procs(alive,timeout=5)
    process.wait(timeout=15)
