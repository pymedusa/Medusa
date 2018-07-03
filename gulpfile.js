#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const gulp = require('gulp');
const workDir = process.cwd();
const pathToFolder = path.join(workDir, 'themes-default');
const execa = require('execa');

const build = done => {
    // Place code for your default task here
    done();
};

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

gulp.task('default', ['lintthemes']);
gulp.task('build', build);
gulp.task('lintthemes', () => {
    const folders = getFolders(pathToFolder);
    return Promise.all(folders.map(folder => {
        const fullPath = path.join(pathToFolder, folder);
        return lintTheme(fullPath);
    }));
});
