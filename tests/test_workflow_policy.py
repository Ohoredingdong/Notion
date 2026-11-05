"""Policy regressions mutate temporary fixtures, never operational workflows."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workflow_policy',ROOT/'scripts/check_workflow_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class WorkflowPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'.github/workflows',self.root/'.github/workflows')
        (self.root/'docs').mkdir()
        shutil.copy2(ROOT/'docs/development-workflow-inventory.json',self.root/'docs/development-workflow-inventory.json')
        shutil.copy2(ROOT/'.github/release-policy.json',self.root/'.github/release-policy.json')

    def mutate(self,name,old,new):
        p=self.root/'.github/workflows'/name;s=p.read_text();self.assertIn(old,s);p.write_text(s.replace(old,new,1))

    def assertRejected(self,part):
        result=policy.check(self.root);self.assertFalse(result['passed'])
        self.assertTrue(any(part in message for message in result['errors']),result['errors'])

    def test_current_configuration_passes(self): self.assertTrue(policy.check(self.root)['passed'],policy.check(self.root)['errors'])
    def test_deleted_collector_is_rejected(self):
        (self.root/'.github/workflows/update-stock-value-radar.yml').unlink();self.assertRejected('existing automation retained')
    def test_schedule_cannot_be_silently_removed(self):
        self.mutate('update-stock-value-radar.yml','15 3,13 * * *','15 3 * * *');self.assertRejected('schedule trigger retained')
    def test_collector_permission_reduction_is_detected(self):
        self.mutate('update-stock-value-radar.yml','contents: write','contents: read');self.assertRejected('publisher permissions unchanged')
    def test_publisher_command_is_preserved(self):
        self.mutate('update-stock-value-radar.yml','git push && exit 0','echo disabled && exit 0');self.assertRejected('publication retained')
    def test_foreign_or_failed_predecessor_guard_is_required(self):
        self.mutate('verify-stock-official.yml',"github.event.workflow_run.conclusion == 'success'","github.event.workflow_run.conclusion != 'cancelled'");self.assertRejected('failed or foreign predecessor')
    def test_data_updates_do_not_continuously_cancel_running_validation(self):
        self.mutate('change-validation.yml',"cancel-in-progress: ${{ github.event_name != 'workflow_run' }}",'cancel-in-progress: true');self.assertRejected('without starving')
    def test_no_duplicate_yaml_keys(self):
        with (self.root/'.github/workflows/change-validation.yml').open('a') as out:out.write('\npermissions:\n  contents: write\n')
        self.assertRejected('duplicate YAML key')
    def test_pull_request_target_not_allowed(self):
        self.mutate('change-validation.yml','pull_request:','pull_request_target:');self.assertRejected('pull_request_target')
    def test_required_check_never_disappears_via_path_filters(self):
        self.mutate('change-validation.yml','pull_request:\n    branches: [main]','pull_request:\n    branches: [main]\n    paths: ["*.html"]');self.assertRejected('no path-filter pending')
    def test_automatic_release_trigger_is_rejected(self):
        self.mutate('reviewed-pages-release.yml','on:\n','on:\n  push:\n    branches: [main]\n');self.assertRejected('no automatic event trigger')
    def test_live_activation_requires_a_separate_review(self):
        p=self.root/'.github/release-policy.json';data=json.loads(p.read_text());data['enabled']=True;p.write_text(json.dumps(data));self.assertRejected('activation remains disabled')
    def test_comparison_step_produces_real_newlines_and_exact_commits(self):
        repo=self.root/'fixture-git';repo.mkdir()
        def command(*args):
            return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
        command('init','--initial-branch=main')
        command('config','user.name','Policy fixture')
        command('config','user.email','fixture@example.invalid')
        (repo/'sample').write_text('before');command('add','sample');command('commit','-m','before')
        base=command('rev-parse','HEAD')
        (repo/'sample').write_text('after');command('add','sample');command('commit','-m','after')
        head=command('rev-parse','HEAD')
        workflow=policy.read_workflow(self.root/'.github/workflows/change-validation.yml')
        step=next(step for step in workflow['jobs']['verify']['steps'] if step.get('id')=='comparison')
        for event in ('pull_request','push','workflow_run','workflow_dispatch'):
            with self.subTest(event=event):
                output=self.root/(event+'-output')
                env=dict(os.environ,EVENT_NAME=event,PR_BASE=base,PUSH_BEFORE=base,PRODUCER_HEAD=head,GITHUB_OUTPUT=str(output))
                subprocess.run(['bash','-e','-c',step['run']],cwd=repo,env=env,capture_output=True,text=True,check=True)
                self.assertEqual(output.read_text(),f'base={base}\nhead={head}\n')
        output=self.root/'invalid-output'
        env=dict(os.environ,EVENT_NAME='pull_request',PR_BASE='not-a-commit',GITHUB_OUTPUT=str(output))
        result=subprocess.run(['bash','-e','-c',step['run']],cwd=repo,env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(output.exists())

    def test_readonly_validation_cannot_publish(self):
        self.mutate('change-validation.yml','python scripts/check_workflow_policy.py','git push origin HEAD:main\n          python scripts/check_workflow_policy.py');self.assertRejected('cannot publish')


if __name__=='__main__':unittest.main(verbosity=2)
