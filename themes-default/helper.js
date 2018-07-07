#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const execa = require('execa');

const getFolders = dir => {
    return fs.readdirSync(dir)
        .filter(function(file) {
            return fs.statSync(path.join(dir, file)).isDirectory();
        });
};

const lintTheme = theme => {
    console.log(`Starting lint of ${theme}`);
    const stream = execa('yarn', [], {cwd: theme});
    stream.stdout.pipe(process.stdout);
    return stream
        .catch(error => {
            console.log(`Lint errored for theme ${theme}`);
            process.exit(error.code);
        });
};

const lintThemes = () => {
    const folders = getFolders(__dirname);
    return Promise.all(folders.map(folder => {
        const fullPath = path.join(__dirname, folder);
        return lintTheme(fullPath);
    }));
};

require('yargs') // eslint-disable-line
    .command('lint', 'lint themes', () => {}, (argv) => {
        lintThemes();
    })
    .demandCommand(1, 'You need at least one command before moving on')
    .help()
    .argv
