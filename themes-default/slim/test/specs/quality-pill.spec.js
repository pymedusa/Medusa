import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue } from '@vue/test-utils';
import { QualityPill } from '../../src/components';
import { generatePropTest } from '../helpers/generators';
import fixtures from '../__fixtures__/common';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
});

const pillTestCase = generatePropTest(QualityPill);

test('renders quality pills correctly', t => {
    pillTestCase(t, 'No qualities', {
        quality: 0
    });

    pillTestCase(t, 'No qualities, with show-title', {
        quality: 0,
        showTitle: true
    });

    pillTestCase(t, 'Unknown, allowed', {
        quality: 1
    });

    pillTestCase(t, 'SDTV, allowed', {
        quality: 2
    });

    pillTestCase(t, 'SD DVD, allowed', {
        quality: 4
    });

    pillTestCase(t, 'RawHD, allowed', {
        quality: 16
    });

    pillTestCase(t, 'SD (TV+DVD), allowed', {
        quality: 2 | 4
    });

    pillTestCase(t, '1080p WEB-DL, allowed', {
        quality: 128
    });

    pillTestCase(t, 'All 720p and all 1080p, allowed', {
        quality: 8 | 32 | 64 | 128 | 256 | 512
    });

    pillTestCase(t, 'WEB-DL 720p + 4K UHD WEB-DL, allowed', {
        quality: 128 | 2048
    });

    pillTestCase(t, '720p WEB-DL allowed + 1080p WEB-DL preferred, with show title', {
        quality: 64 | (128 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Custom pill using overrides', {
        quality: 0,
        override: {
            class: 'quality Proper',
            text: 'Proper',
            title: 'Show.Name.S03E15.720p.Proper.HDTV.x264-Group.mkv'
        }
    });

    pillTestCase(t, 'Quality set: Any HDTV, with show title', {
        quality: 40,
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of HDTV source, with show title', {
        quality: (8 | 32) | (1024 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of WEB-DL source, with show title', {
        quality: (64 | 128) | (2048 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of BluRay source, with show title', {
        quality: (256 | 512) | ((4096 | 32768) << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of 720p resolution, with show title', {
        quality: (8 | 64) | (256 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of 1080p resolution, with show title', {
        quality: (32 | 128) | (512 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of 4K UHD resolution, with show title', {
        quality: (1024 | 2048) | (4096 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Both quality lists are of 8K UHD resolution, with show title', {
        quality: (8192 | 16384) | (32768 << 16),
        showTitle: true
    });

    pillTestCase(t, 'Custom quality lists, with show title', {
        quality: (2 | 8 | 64 | 256 | 512) | ((2048 | 4096) << 16),
        showTitle: true
    });
});
