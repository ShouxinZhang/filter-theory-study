"""跨可执行程序验证在线因果性，冻结数据和作业恢复。"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline import dataset, jobs
from pipeline.common import command, digest_file

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "build").symlink_to(ROOT / "build", target_is_directory=True)
        self.old_dataset_root, self.old_jobs_root = dataset.ROOT, jobs.ROOT
        dataset.ROOT = jobs.ROOT = self.root
        self.spec = {"model": "gordon", "steps": 8, "trials": 1, "seed": 741}
        self.directory, self.manifest = dataset.ensure_dataset(self.spec)

    def tearDown(self):
        dataset.ROOT, jobs.ROOT = self.old_dataset_root, self.old_jobs_root
        self.temp.cleanup()

    def run_filter(self, observation, output, algorithm):
        subprocess.run(command(ROOT / "build/filter", model="gordon", observations=observation,
            output=output, algorithm=algorithm, n=16, epsilon=1, interval=4,
            max_iterations=50, seed=123), check=True, capture_output=True)
        with output.open() as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row.pop("predict_us")
            row.pop("update_us")
        return rows

    def test_future_and_missing_observations(self):
        original = self.directory / self.manifest["trials"][0]["observations"]
        lines = original.read_text().splitlines()
        changed = self.root / "changed.csv"
        # 非观测步全部改动，唯一未来观测 k=8 也改动，前7步必须完全不变
        revised = [lines[0]] + [line if i == 4 else str(i) + ",9999"
                                for i, line in enumerate(lines[1:], 1)]
        changed.write_text("\n".join(revised) + "\n")
        for algorithm in ("ekf", "bpf", "enkf", "etpf"):
            before = self.run_filter(original, self.root / (algorithm + "_a.csv"), algorithm)
            after = self.run_filter(changed, self.root / (algorithm + "_b.csv"), algorithm)
            self.assertEqual(before[:7], after[:7], algorithm)

    def test_resume_and_corruption(self):
        config = {"dataset": self.spec, "algorithm_seed": 987,
                  "solver": {"tolerance": 1e-8, "max_iterations": 50}, "intervals": [1, 4]}
        cfg = {"config_id": "bpf_n16_e0_m4", "algorithm": "bpf", "n": 16, "epsilon": 0, "interval": 4}
        task = (self.root / "run", self.directory, self.manifest, self.manifest["trials"][0], config, cfg)
        first = jobs.execute_job(task)
        self.assertEqual(first["state"], "complete")
        second = jobs.execute_job(task)
        self.assertTrue(second["skipped"])
        output = Path(first["folder"]) / "filter.csv"
        output.write_text("corrupted\n")
        repaired = jobs.execute_job(task)
        self.assertEqual(repaired["state"], "complete")
        self.assertNotIn("skipped", repaired)
        # 时钟列允许变化，修复结果的哈希必须与新状态一致
        self.assertEqual(digest_file(output), repaired["outputs"]["filter.csv"])

    def test_frozen_dataset_integrity(self):
        again, manifest = dataset.ensure_dataset(self.spec)
        self.assertEqual(manifest, self.manifest)
        observations = again / manifest["trials"][0]["observations"]
        observations.write_text(observations.read_text() + "9,1\n")
        with self.assertRaisesRegex(RuntimeError, "冻结基准"):
            dataset.ensure_dataset(self.spec)

if __name__ == "__main__":
    unittest.main()
