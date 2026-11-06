"""Check the real stock refresh graph against GitHub's workflow_run depth limit.

An explicit dispatch starts a fresh chain. A fourth workflow_run edge cannot
be relied on, even when every producer succeeds. Tests use only workflow text;
they never contact providers, dispatch a job, or change production data.
"""
import ast
import re
import unittest
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'update-stock-value-radar.yml', 'verify-stock-official.yml',
    'update-stock-opportunities.yml', 'stock-investment-cases.yml',
    'stock-reading-depth.yml', 'stock-strict-green.yml',
    'stock-recommendations.yml', 'stock-entry-plan.yml',
    'audit-stock-radar-accuracy.yml', 'monitor-stock-value-radar.yml',
    'verify-stock-world-public.yml',
)


def workflow_graph(texts):
    """Read the single-line workflow lists used by these repository workflows."""
    names = {file: re.search(r'^name:\s*(.+)$', text, re.M).group(1).strip().strip('\"\'')
             for file, text in texts.items()}
    edges = {name: set() for name in names.values()}
    for file, text in texts.items():
        workflow_lists = re.findall(r'^\s+workflows:\s*(\[[^\n]*\])\s*$', text, re.M)
        if re.search(r'^  workflow_run:', text, re.M) and not workflow_lists:
            raise ValueError('Unparsed workflow_run list: ' + file)
        for parent_list in workflow_lists:
            for parent in ast.literal_eval(parent_list):
                if parent in edges:
                    edges[parent].add((names[file], 'workflow_run'))
        for target in re.findall(r'/actions/workflows/([^/\s\"]+)/dispatches', text):
            if target in names:
                edges[names[file]].add((names[target], 'workflow_dispatch'))
    return edges


def reachable(graph, initial):
    visited = set()
    pending = deque([(initial, 0)])
    while pending:
        node, depth = pending.popleft()
        if (node, depth) in visited:
            continue
        visited.add((node, depth))
        for target, kind in graph[node]:
            if kind == 'workflow_dispatch':
                pending.append((target, 0))
            elif depth < 3:
                pending.append((target, depth + 1))
    return {node for node, _ in visited}


class RefreshHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {name: (ROOT / '.github' / 'workflows' / name).read_text()
                     for name in FILES}
        cls.graph = workflow_graph(cls.texts)

    def test_longest_regular_source_chain_reaches_every_terminal_stage(self):
        expected = {'Stock Three-Year Reading', 'Strict Green Review',
                    'Stock Recommendations', 'Stock Entry Plan',
                    'Audit Stock Radar Accuracy', 'Monitor Stock Radar Health',
                    'Verify Public World Market Update'}
        self.assertFalse(expected - reachable(self.graph, 'Update Stock Value Radar'))

    def test_without_case_dispatch_the_observed_fourth_hop_is_blocked(self):
        graph = {node: set(edges) for node, edges in self.graph.items()}
        graph['Stock Investment Cases'].discard(('Stock Three-Year Reading', 'workflow_dispatch'))
        graph['Stock Investment Cases'].add(('Stock Three-Year Reading', 'workflow_run'))
        self.assertNotIn('Stock Three-Year Reading', reachable(graph, 'Update Stock Value Radar'))

    def test_dispatch_runs_only_after_publication_and_ui_validation(self):
        cases = self.texts['stock-investment-cases.yml']
        target = '/actions/workflows/stock-reading-depth.yml/dispatches'
        self.assertEqual(cases.count(target), 1)
        self.assertLess(cases.index('python scripts/publish_widget_data.py'), cases.index(target))
        self.assertLess(cases.index('python scripts/publish_stock_investment_cases.py'), cases.index(target))
        step = cases[cases.rfind('      - name:', 0, cases.index(target)):cases.index(target)]
        self.assertIn("if: success() && github.ref == 'refs/heads/main'", step)
        self.assertIn('GH_TOKEN: ${{ github.token }}', step)
        self.assertIn('  actions: write', cases)
        self.assertIn('github.event.workflow_run.head_repository.full_name == github.repository', cases)

    def test_case_publication_does_not_schedule_duplicate_downstream_jobs(self):
        self.assertNotRegex(self.texts['stock-reading-depth.yml'], re.compile(r'^  workflow_run:', re.M))
        self.assertEqual(self.graph['Stock Investment Cases'],
                         {('Stock Three-Year Reading', 'workflow_dispatch'),
                          ('Audit Stock Radar Accuracy', 'workflow_run'),
                          ('Monitor Stock Radar Health', 'workflow_run')})
        self.assertIn(('Strict Green Review', 'workflow_run'), self.graph['Stock Three-Year Reading'])

    def test_public_proof_starts_after_the_successful_audit_publication(self):
        audit = self.texts['audit-stock-radar-accuracy.yml']
        target = '/actions/workflows/verify-stock-world-public.yml/dispatches'
        self.assertEqual(audit.count(target), 1)
        self.assertLess(audit.index('python scripts/publish_stock_radar_audit.py'), audit.index(target))
        self.assertLess(audit.index('/pages/builds'), audit.index(target))
        step = audit[audit.rfind('      - name:', 0, audit.index(target)):audit.index(target)]
        self.assertNotIn('always()', step)
        self.assertIn('  actions: write', audit)
        self.assertIn('  workflow_dispatch:', self.texts['verify-stock-world-public.yml'])

    def test_tracked_refresh_graph_cannot_dispatch_back_into_itself(self):
        completed = set()
        active = set()

        def visit(node):
            self.assertNotIn(node, active, 'Refresh workflows form a trigger cycle')
            if node in completed:
                return
            active.add(node)
            for target, _ in self.graph[node]:
                visit(target)
            active.remove(node)
            completed.add(node)

        for node in self.graph:
            visit(node)


if __name__ == '__main__':
    unittest.main()
