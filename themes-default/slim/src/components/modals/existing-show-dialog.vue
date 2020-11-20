<template>
    <transition name="modal">
        <div class="modal-mask">
            <div class="modal-wrapper">
                <div class="modal-content">
                    <div class="modal-header">
                        Existing show folder metadata found
                    </div>

                    <div class="modal-body">
                        <p>The folder for the selected show already exists. And metadata was found.<br>The show has previously been added through the indexer <strong>{{indexerName}}</strong>.<br>Do you want to use this indexer?</p>
                    </div>

                    <div class="v-modal-footer">
                        <!-- <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="eventCallback({answer: 'no'}); $emit('close')">No</button>
                        <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="eventCallback({answer: 'yes'}); $emit('close')">Yes</button> -->
                        <div class="modal-button" @click="eventCallback({answer: 'yes'}); $emit('close')">yes</div>
                        <div class="modal-button" @click="eventCallback({answer: 'no'}); $emit('close')">no</div>
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
export default {
    props: {
        indexerName: String,
        eventCallback: Function
    }
};
</script>
<style scoped>
.v-modal-footer {
    display: flex;
}

.v-modal-footer > div {
    flex: 1;
    text-align: center;
    border: 1px solid rgba(0, 0, 0, 0.2);
    background: linear-gradient(to bottom, #242424 5%, #555 100%);
    background-color: #242424;
    display: inline-block;
    cursor: pointer;
    color: #fff;
    font-size: 15px;
    font-weight: bold;
    padding: 11px 23px;
    text-decoration: none;
    text-shadow: 0 -1px 0 #0a0d12;
}

.v-modal-footer > div:hover {
    background: linear-gradient(to bottom, #555 5%, #242424 100%);
    background-color: #555;
}

.v-modal-footer > div:hover:active {
    position: relative;
    top: 1px;
}

</style>
