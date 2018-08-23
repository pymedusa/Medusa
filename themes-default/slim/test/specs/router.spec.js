import test from 'ava';
import router from '../../src/router';

test('router compiles', t => {
    t.truthy(router);
});
