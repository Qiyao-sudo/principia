#!/usr/bin/env node
import { execSync } from 'child_process';

function detectPython() {
  const commands = ['python3', 'python', 'py'];
  
  for (const cmd of commands) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      console.log(cmd);
      return;
    } catch {
      continue;
    }
  }
  
  console.error('Error: No Python command found. Please install Python.');
  process.exit(1);
}

detectPython();
