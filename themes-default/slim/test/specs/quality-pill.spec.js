/* eslint jest/expect-expect: ["error", { "assertFunctionNames": ["expect", "pillTestCase"] }] */
import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue } from '@vue/test-utils';
import { QualityPill } from '../../src/components';
import consts from '../../src/store/modules/config/consts';
import { generatePropTest } from '../helpers/generators';
import fixtures from '../__fixtures__/common';

describe('QualityPill.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({
            modules: {
                consts: {
                    getters: consts.getters,
                    state: state.config.consts
                },
                config: {
                    state: state.config
                }
            }
        });
    });

    const pillTestCase = generatePropTest(QualityPill);

    it('renders quality pills correctly', () => {
        pillTestCase(localVue, store, 'No qualities', {
            quality: 0
        });

        pillTestCase(localVue, store, 'No qualities, with show-title', {
            quality: 0,
            showTitle: true
        });

        pillTestCase(localVue, store, 'Unknown, allowed', {
            quality: 1
        });

        pillTestCase(localVue, store, 'SDTV, allowed', {
            quality: 2
        });

        pillTestCase(localVue, store, 'SD DVD, allowed', {
            quality: 4
        });

        pillTestCase(localVue, store, 'RawHD, allowed', {
            quality: 16
        });

        pillTestCase(localVue, store, 'SD (TV+DVD), allowed', {
            quality: 2 | 4
        });

        pillTestCase(localVue, store, '1080p WEB-DL, allowed', {
            quality: 128
        });

        pillTestCase(localVue, store, 'All 720p and all 1080p, allowed', {
            quality: 8 | 32 | 64 | 128 | 256 | 512
        });

        pillTestCase(localVue, store, 'All 4K and all 8K, allowed', {
            quality: 1024 | 2048 | 4096 | 8192 | 16384 | 32768
        });

        pillTestCase(localVue, store, 'WEB-DL 720p + 4K UHD WEB-DL, allowed', {
            quality: 128 | 2048
        });

        pillTestCase(localVue, store, '720p WEB-DL allowed + 1080p WEB-DL preferred, with show title', {
            quality: 64 | (128 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Custom pill using overrides', {
            quality: 0,
            override: {
                class: 'quality Proper',
                text: 'Proper',
                title: 'Show.Name.S03E15.720p.Proper.HDTV.x264-Group.mkv'
            }
        });

        pillTestCase(localVue, store, 'Quality set: Any HDTV, with show title', {
            quality: 40,
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of HDTV source, with show title', {
            quality: (8 | 32) | (1024 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of WEB-DL source, with show title', {
            quality: (64 | 128) | (2048 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of BluRay source, with show title', {
            quality: (256 | 512) | ((4096 | 32768) << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of 720p resolution, with show title', {
            quality: (8 | 64) | (256 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of 1080p resolution, with show title', {
            quality: (32 | 128) | (512 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of 4K UHD resolution, with show title', {
            quality: (1024 | 2048) | (4096 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Both quality lists are of 8K UHD resolution, with show title', {
            quality: (8192 | 16384) | (32768 << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, 'Custom quality lists, with show title', {
            quality: (2 | 8 | 64 | 256 | 512) | ((2048 | 4096) << 16),
            showTitle: true
        });

        pillTestCase(localVue, store, '720p Preset', {
            quality: 328,
            showTitle: true
        });

        pillTestCase(localVue, store, '1080p Preset', {
            quality: 672,
            showTitle: true
        });
    });
});
