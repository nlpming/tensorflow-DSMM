
import tensorflow as tf

from models.match_pyramid import MatchPyramidBaseModel
from tf_common.nn_module import dense_block, resnet_block


class DSMM(MatchPyramidBaseModel):
    def __init__(self, model_name, params, logger, threshold, calibration_factor, training=True,
                 word_embedding_matrix=None, char_embedding_matrix=None):
        super(DSMM, self).__init__(model_name, params, logger, threshold, calibration_factor, training,
                                            word_embedding_matrix, char_embedding_matrix)

    def _build_model(self):
        with tf.name_scope(self.model_name):
            tf.set_random_seed(self.params["random_seed"])

            with tf.name_scope("word_network"):
                sem_seq_word_left, enc_seq_word_left = self._semantic_feature_layer(self.seq_word_left, granularity="word", reuse=False, return_enc=True)
                sem_seq_word_right, enc_seq_word_right = self._semantic_feature_layer(self.seq_word_right, granularity="word", reuse=True, return_enc=True)

                #### matching
                # cosine similarity
                # sem_seq_word_left = tf.nn.l2_normalize(sem_seq_word_left, dim=1)
                # sem_seq_word_right = tf.nn.l2_normalize(sem_seq_word_right, dim=1)
                sim_word = sem_seq_word_left * sem_seq_word_right

                # diff
                diff_word = tf.abs(sem_seq_word_left - sem_seq_word_right)

                # fm
                tmp = tf.concat([enc_seq_word_left, enc_seq_word_right], axis=1)
                sum_squared = tf.square(tf.reduce_sum(tmp, axis=1))
                squared_sum = tf.reduce_sum(tf.square(tmp), axis=1)
                fm_word = 0.5 * (sum_squared - squared_sum)

                # match pyramid
                cross_word = self._interaction_feature_layer(enc_seq_word_left, enc_seq_word_right, self.dpool_index_word, granularity="word")

                # dense
                deep_in_word = tf.concat([sem_seq_word_left, sem_seq_word_right], axis=-1)
                hidden_units = self.params["fc_hidden_units"]
                dropouts = self.params["fc_dropouts"]
                if self.params["fc_type"] == "fc":
                    deep_word = dense_block(deep_in_word, hidden_units=hidden_units, dropouts=dropouts, densenet=False,
                                                scope_name=self.model_name + "deep_word", reuse=False,
                                                training=self.training, seed=self.params["random_seed"])
                elif self.params["fc_type"] == "densenet":
                    deep_word = dense_block(deep_in_word, hidden_units=hidden_units, dropouts=dropouts, densenet=True,
                                                scope_name=self.model_name + "deep_word", reuse=False,
                                                training=self.training, seed=self.params["random_seed"])
                elif self.params["fc_type"] == "resnet":
                    deep_word = resnet_block(deep_in_word, hidden_units=hidden_units, dropouts=dropouts, cardinality=1,
                                                 dense_shortcut=True, training=self.training,
                                                 seed=self.params["random_seed"],
                                                 scope_name=self.model_name + "deep_word", reuse=False)

            with tf.name_scope("char_network"):
                sem_seq_char_left, enc_seq_char_left = self._semantic_feature_layer(self.seq_char_left, granularity="char", reuse=False, return_enc=True)
                sem_seq_char_right, enc_seq_char_right = self._semantic_feature_layer(self.seq_char_right, granularity="char", reuse=True, return_enc=True)

                #### matching
                # cosine similarity
                # sem_seq_char_left = tf.nn.l2_normalize(sem_seq_char_left, dim=1)
                # sem_seq_char_right = tf.nn.l2_normalize(sem_seq_char_right, dim=1)
                sim_char = sem_seq_char_left * sem_seq_char_right

                # diff
                diff_char = tf.abs(sem_seq_char_left - sem_seq_char_right)

                # fm
                tmp = tf.concat([enc_seq_char_left, enc_seq_char_right], axis=1)
                sum_squared = tf.square(tf.reduce_sum(tmp, axis=1))
                squared_sum = tf.reduce_sum(tf.square(tmp), axis=1)
                fm_char = 0.5 * (sum_squared - squared_sum)

                # match pyramid
                cross_char = self._interaction_feature_layer(enc_seq_char_left, enc_seq_char_right,
                                                             self.dpool_index_char,
                                                             granularity="char")

                # dense
                deep_in_char = tf.concat([sem_seq_char_left, sem_seq_char_right], axis=-1)
                hidden_units = self.params["fc_hidden_units"]
                dropouts = self.params["fc_dropouts"]
                if self.params["fc_type"] == "fc":
                    deep_char = dense_block(deep_in_char, hidden_units=hidden_units, dropouts=dropouts, densenet=False,
                                                scope_name=self.model_name + "deep_char", reuse=False,
                                                training=self.training, seed=self.params["random_seed"])
                elif self.params["fc_type"] == "densenet":
                    deep_char = dense_block(deep_in_char, hidden_units=hidden_units, dropouts=dropouts, densenet=True,
                                                scope_name=self.model_name + "deep_char", reuse=False,
                                                training=self.training, seed=self.params["random_seed"])
                elif self.params["fc_type"] == "resnet":
                    deep_char = resnet_block(deep_in_char, hidden_units=hidden_units, dropouts=dropouts, cardinality=1,
                                                 dense_shortcut=True, training=self.training,
                                                 seed=self.params["random_seed"],
                                                 scope_name=self.model_name + "deep_char", reuse=False)

            with tf.name_scope("prediction"):
                out_0 = tf.concat([
                    sim_word, cross_word,
                    sim_char, cross_char,
                ], axis=-1)
                hidden_units = self.params["fc_hidden_units"]
                dropouts = self.params["fc_dropouts"]
                if self.params["fc_type"] == "fc":
                    out = dense_block(out_0, hidden_units=hidden_units, dropouts=dropouts, densenet=False,
                                      scope_name=self.model_name + "mlp", reuse=False, training=self.training,
                                      seed=self.params["random_seed"])
                elif self.params["fc_type"] == "densenet":
                    out = dense_block(out_0, hidden_units=hidden_units, dropouts=dropouts, densenet=True,
                                      scope_name=self.model_name + "mlp", reuse=False, training=self.training,
                                      seed=self.params["random_seed"])
                elif self.params["fc_type"] == "resnet":
                    out = resnet_block(out_0, hidden_units=hidden_units, dropouts=dropouts, cardinality=1,
                                       dense_shortcut=True, training=self.training,
                                       seed=self.params["random_seed"], scope_name=self.model_name + "mlp", reuse=False)
                logits = tf.layers.dense(out, 1, activation=None,
                                         kernel_initializer=tf.glorot_uniform_initializer(
                                             seed=self.params["random_seed"]),
                                         name=self.model_name + "logits")
                logits = tf.squeeze(logits, axis=1)
                proba = tf.nn.sigmoid(logits)

            with tf.name_scope("loss"):
                loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=self.labels, logits=logits)
                loss = tf.reduce_mean(loss, name="log_loss")
                if self.params["l2_lambda"] > 0:
                    l2_losses = tf.add_n(
                        [tf.nn.l2_loss(v) for v in tf.trainable_variables() if 'bias' not in v.name]) * self.params[
                                    "l2_lambda"]
                    loss = loss + l2_losses

        return loss, logits, proba