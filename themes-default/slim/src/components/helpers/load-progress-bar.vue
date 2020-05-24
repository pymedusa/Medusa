<template>
    <div v-if="display" class="load-progress-bar-container">
        <div class="border">
            <div class="msg">{{loadMsg}}</div>
            <div class="progress" :style="styleProgress" />
        </div>
    </div>
</template>
<script>

export default {
    name: 'load-progress-bar',
    props: {
        display: Boolean,
        current: Number,
        total: Number,
        description: {
            type: String,
            default: 'Shows'
        }
    },
    computed: {
        loadMsg() {
            const { current, total, description } = this;
            return `Loaded ${current} out of ${total} ${description}`;
        },
        styleProgress() {
            const { current, total } = this;
            return ({
                height: '24px',
                width: `${Math.round(current / total * 100)}%`
            });
        }
    }
};
</script>
<style>
.load-progress-bar-container {
    position: absolute;
    bottom: 0;
    right: 0;
}

.border {
    box-sizing: border-box;
    height: 26px;
    text-size-adjust: 100%;
    width: 382px;
    perspective-origin: 191px 13px;
    transform-origin: 191px 13px;
    border: 1px solid #ccc;
    border-radius: 5px;
}

@media (max-width: 767px) {
    .border {
        width: 100%;
    }

    .load-progress-bar-container {
        width: 100%;
    }
}

.progress {
    box-sizing: border-box;
    height: 24px;
    text-size-adjust: 100%;
    width: 76px;
    perspective-origin: 38px 12px;
    transform-origin: 38px 12px;
    background: rgba(99, 177, 137, 0.63) none repeat scroll 0% 0% / auto padding-box border-box;
}

.msg {
    position: absolute;
    padding: 3px 5px 0 5px;
}

</style>
