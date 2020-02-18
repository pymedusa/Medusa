<template>
  <div id="search-template-pattern">
    <div class="row">
      <label class="col-sm-2 control-label">
        <span>&nbsp;</span>
      </label>
      <div class="col-sm-10 content">
        <div class="tooltip-wrapper" v-tooltip.right="{content: tooltipContent}">
          <input
            :class="{invalid: !validated}"
            type="text"
            name="search_pattern"
            :disabled="searchTemplate.default"
            v-model="searchTemplate.template"
            @change="updateExample"
            @input="update()"
            class="form-control-inline-max input-sm max-input350 search-pattern"
          />
        </div>
        <input type="checkbox" v-model="searchTemplate.enabled" />
        <i
          class="show-template glyphicon"
          :class="`glyphicon-eye-${showExample ? 'close' : 'open'}`"
          @click="showExample = !showExample"
          title="Show template example"
        />
        <span
          :class="{invalid: !validated}"
          class="template-example"
          v-if="showExample"
          name="search_pattern"
        >Example: {{searchTemplateExample}}</span>
      </div>
    </div>
  </div>
</template>

<script>
import formatDate from "date-fns/format";
import { apiRoute } from "../../api";
import { VTooltip } from "v-tooltip";

export default {
  name: "search-template-pattern",
  directives: {
    tooltip: VTooltip
  },
  props: {
    /**
     * Provide the custom naming type. -Like sports, anime, air by date- description.
     * If none provided we asume this is the default episode naming component.
     * And that means there will be no checkbox available to enable/disable it.
     */
    format: {
      type: String,
      default: ""
    },
    template: {
      type: Object
    },
    season: {
      type: Boolean,
      default: false
    },
    animeType: {
      type: Number,
      default: 3
    }
  },
  data() {
    return {
      showFormat: null,
      searchTemplate: "",
      searchTemplateExample: "",
      showExample: false,
      validated: true,
      seasonPattern: false
    };
  },
  computed: {
    tooltipContent() {
      const { searchTemplate } = this;
      return searchTemplate.default
        ? "This template has been generated based on a scene exception / title. It's a default template and cannot be modified. It can only be enabled/disabled."
        : "You can modify this template. On changing the template, it will be tested against the template rules. And shown red if not valid.";
    }
  },
  methods: {
    getDateFormat(format) {
      return formatDate(new Date(), format);
    },
    async checkNaming(template) {
      const { animeType, showFormat } = this;
      if (!template) {
        return;
      }

      let params = {
        pattern: template.template
      };
      const formatMap = new Map([
        ["anime", { anime_type: animeType }],
        ["sports", { sports: true }],
        ["airByDate", { abd: true }]
      ]);

      if (showFormat !== "") {
        params = { ...params, ...formatMap.get(showFormat) };
      }

      this.validated = false;
      try {
        const response = await apiRoute.get(
          "config/postProcessing/isNamingValid",
          { params, timeout: 20000 }
        );
        if (response.data !== "invalid") {
          this.validated = true;
        }
      } catch (error) {
        console.warn(error);
      }
    },
    async testNaming(template) {
      const { animeType, showFormat } = this;
      console.debug(`Test pattern ${template.template}`);

      let params = {
        pattern: template.template
      };

      const formatMap = new Map([
        ["anime", { anime_type: animeType }],
        ["sports", { sports: true }],
        ["airByDate", { abd: true }]
      ]);

      if (showFormat !== "") {
        params = { ...params, ...formatMap.get(showFormat) };
      }

      let response = "";

      try {
        response = await apiRoute.get("config/postProcessing/testNaming", {
          params,
          timeout: 20000
        });
        this.searchTemplateExample = response.data;
      } catch (error) {
        console.warn(error);
      }
      return response;
    },
    updateExample() {
      const { searchTemplate, showFormat, testNaming } = this;

      // Test naming
      this.checkNaming(searchTemplate, false, showFormat);

      // Update single
      testNaming(searchTemplate, false, this.showFormat);
    },
    update() {
      this.$nextTick(() => {
        this.$emit("change", {
          template: this.searchTemplate,
          format: this.showFormat
        });
      });
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
    const { format, season, template } = this;
    this.searchTemplate = template;
    this.showFormat = format;
    this.seasonPattern = season;

    // Update the pattern example
    this.updateExample();
  },
  watch: {
    template(newTemplate, oldTemplate) {
      this.searchTemplate = newTemplate;
      this.updateExample();
    },
    animeType() {
        this.updateExample();
    }
  }
};
</script>
<style>
.show-template {
  left: -8px;
  top: 4px;
  position: absolute;
  z-index: 10;
  opacity: 0.6;
}

.template-example {
  display: block;
  line-height: 20px;
  margin-bottom: 15px;
  padding: 2px 5px 2px 2px;
  clear: left;
  max-width: 338px;
}

.tooltip-wrapper {
  float: left;
  min-width: 340px;
}

.invalid {
  background-color: #ff5b5b;
}

.tooltip {
  display: block !important;
  z-index: 10000;
}

.tooltip .tooltip-inner {
  background: #ffef93;
  color: #555;
  border-radius: 16px;
  padding: 5px 10px 4px;
  border: 1px solid #f1d031;
  -webkit-box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
  -moz-box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
  box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
}

.tooltip .tooltip-arrow {
  width: 0;
  height: 0;
  position: absolute;
  margin: 5px;
  border: 1px solid #ffef93;
  z-index: 1;
}

.tooltip[x-placement^="top"] {
  margin-bottom: 5px;
}

.tooltip[x-placement^="top"] .tooltip-arrow {
  border-width: 5px 5px 0 5px;
  border-left-color: transparent !important;
  border-right-color: transparent !important;
  border-bottom-color: transparent !important;
  bottom: -5px;
  left: calc(50% - 4px);
  margin-top: 0;
  margin-bottom: 0;
}

.tooltip[x-placement^="bottom"] {
  margin-top: 5px;
}

.tooltip[x-placement^="bottom"] .tooltip-arrow {
  border-width: 0 5px 5px 5px;
  border-left-color: transparent !important;
  border-right-color: transparent !important;
  border-top-color: transparent !important;
  top: -5px;
  left: calc(50% - 4px);
  margin-top: 0;
  margin-bottom: 0;
}

.tooltip[x-placement^="right"] {
  margin-left: 5px;
}

.tooltip[x-placement^="right"] .tooltip-arrow {
  border-width: 5px 5px 5px 0;
  border-left-color: transparent !important;
  border-top-color: transparent !important;
  border-bottom-color: transparent !important;
  left: -4px;
  top: calc(50% - 5px);
  margin-left: 0;
  margin-right: 0;
}

.tooltip[x-placement^="left"] {
  margin-right: 5px;
}

.tooltip[x-placement^="left"] .tooltip-arrow {
  border-width: 5px 0 5px 5px;
  border-top-color: transparent !important;
  border-right-color: transparent !important;
  border-bottom-color: transparent !important;
  right: -4px;
  top: calc(50% - 5px);
  margin-left: 0;
  margin-right: 0;
}

.tooltip.popover .popover-inner {
  background: #ffef93;
  color: #555;
  padding: 24px;
  border-radius: 5px;
  box-shadow: 0 5px 30px rgba(black, 0.1);
}

.tooltip.popover .popover-arrow {
  border-color: #ffef93;
}

.tooltip[aria-hidden="true"] {
  visibility: hidden;
  opacity: 0;
  transition: opacity 0.15s, visibility 0.15s;
}

.tooltip[aria-hidden="false"] {
  visibility: visible;
  opacity: 1;
  transition: opacity 0.15s;
}
</style>
