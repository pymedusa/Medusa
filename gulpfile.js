#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const gulp = require('gulp');
const workDir = process.cwd();
const pathToFolder = path.join(workDir, 'themes-default');
const execa = require('execa');
const getStream = require('get-stream');
const xo = require('gulp-xo');

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
    console.log(`Working dir: ${process.cwd()}`);
    const stream = execa('yarn', [], {cwd: theme}).stdout;
    stream.pipe(process.stdout);
    return getStream(stream).then(value => {
        console.log('child output:', value);
    })
        .catch(err => {
            console.log(`Lint errored for theme ${theme} with error:\n${err.toString()}`);
            process.exit(err.code);
        });
};

/**
 * Run all js files through the xo (eslint) linter.
 * FIXME: This apparently doesn't work properly. It is verry slow.
 * Running the linter on the subdirectories using execa is much faster.
 */
const lint = () => {
    return gulp
        .src([
            'themes-default/*/static/js/**/*.js',
            '!themes-default/*/static/js/lib/**',
            '!themes-default/*/static/js/*.min.js',
            '!themes-default/*/static/js/vender.js',
            '!node_modules/**'
        ])
        .pipe(xo())
        .pipe(xo.format())
        .pipe(xo.failAfterError());
};

gulp.task('default', ['lint']);
gulp.task('build', build);
gulp.task('lintthemes', () => {
    const folders = getFolders(pathToFolder);
    return Promise.all(folders.map(folder => {
        const fullPath = path.join(pathToFolder, folder);
        return lintTheme(fullPath);
    }));
});
gulp.task('lint', lint);
