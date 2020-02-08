<template>
    <div id="search-template-pattern">
        <div class="form-group" style="padding-top: 0;">
            <label class="col-sm-2 control-label">
                <span>&nbsp;</span>
            </label>
            <div class="col-sm-10 content">
                <input type="text" name="search_pattern" v-model="searchTemplate.template" @change="updateExample" @input="update()" class="form-control-inline-max input-sm max-input350">
            </div>
        </div>
        <div class="form-group" style="padding-top: 0;">
            <label class="col-sm-2 control-label">
                <span>&nbsp;</span>
            </label>
            <div class="col-sm-10 content">
                <input type="text" name="search_pattern" disabled v-model="searchTemplateExample" class="form-control-inline-max input-sm max-input350">
            </div>
        </div>
    </div>
</template>

<script>
import formatDate from 'date-fns/format';
import { apiRoute } from '../../api';

export default {
    name: 'search-template-pattern',
    props: {
        /**
         * Provide the custom naming type. -Like sports, anime, air by date- description.
         * If none provided we asume this is the default episode naming component.
         * And that means there will be no checkbox available to enable/disable it.
         */
        format: {
            type: String,
            default: ''
        },
        template: {
            type: Object
        }
    },
    data() {
        return {
            showFormat: null,
            searchTemplate: '',
            searchTemplateExample: ''
        };
    },
    methods: {
        getDateFormat(format) {
            return formatDate(new Date(), format);
        },
        testNaming(template) {
            const { showFormat } = this;
            console.debug(`Test pattern ${template.template}`);
            let params = {
                pattern: template.template
            };

            const formatMap = new Map([
                ['anime', { 'anime_type': 3 }],
                ['sports', { sports: true }],
                ['airByDate', { abd: true }]
            ]);

            if (showFormat !== '') {
                params = { ...params, ...formatMap.get(showFormat) };
            }

            try {
                return apiRoute.get('config/postProcessing/testNaming', { params, timeout: 20000 }).then(res => res.data);
            } catch (error) {
                console.warn(error);
                return '';
            }
        },
        updateExample() {
            const { searchTemplate, showFormat } = this;

            // Update single
            this.testNaming(searchTemplate, false, this.showFormat).then(result => {
                this.searchTemplateExample = result;
            });

            // Test naming
            this.checkNaming(searchTemplate, false, showFormat);
        },
        update() {
            this.$nextTick(() => {
                this.$emit('change', {
                    template: this.searchTemplate,
                    format: this.showFormat
                });
            });
        },
        checkNaming(pattern) {
            if (!pattern) {
                return;
            }

            const params = {
                pattern
            };

            const { $el } = this;
            const el = $($el);

            // apiRoute.get('config/postProcessing/isNamingValid', { params, timeout: 20000 }).then(result => {
            //     if (result.data === 'invalid') {
            //         el.find('#naming_pattern').qtip('option', {
            //             'content.text': 'This pattern is invalid.',
            //             'style.classes': 'qtip-rounded qtip-shadow qtip-red'
            //         });
            //         el.find('#naming_pattern').qtip('toggle', true);
            //         el.find('#naming_pattern').css('background-color', '#FFDDDD');
            //     } else if (result.data === 'seasonfolders') {
            //         el.find('#naming_pattern').qtip('option', {
            //             'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
            //             'style.classes': 'qtip-rounded qtip-shadow qtip-red'
            //         });
            //         el.find('#naming_pattern').qtip('toggle', true);
            //         el.find('#naming_pattern').css('background-color', '#FFFFDD');
            //     } else {
            //         el.find('#naming_pattern').qtip('option', {
            //             'content.text': 'This pattern is valid.',
            //             'style.classes': 'qtip-rounded qtip-shadow qtip-green'
            //         });
            //         el.find('#naming_pattern').qtip('toggle', false);
            //         el.find('#naming_pattern').css('background-color', '#FFFFFF');
            //     }
            // }).catch(error => {
            //     console.warn(error);
            // });
        }
        // updateCustomName() {
        //     // Store the custom naming pattern.
        //     if (!this.presetsPatterns.includes(this.pattern)) {
        //         this.customName = this.pattern;
        //     }

        //     // If the custom name is empty, let's use the last selected pattern.
        //     // We'd prefer to cache the last configured custom pattern.
        //     if (!this.customName) {
        //         this.customName = this.lastSelectedPattern;
        //     }
        // }
    },
    mounted() {
        const { format, template } = this;
        this.searchTemplate = template;
        this.showFormat = format;

        // Update the pattern example
        this.updateExample();
    },
    watch: {
        template(newTemplate, oldTemplate) {
            this.searchTemplate = newTemplate;
            this.updateExample();
        }
    }
};
</script>
<style>

</style>
