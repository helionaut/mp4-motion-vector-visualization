#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/frame.h>
#include <libavutil/motion_vector.h>

typedef struct {
    int frame_index;
    double timestamp_seconds;
    char pict_type;
    int vector_count;
    int motion_vector_side_data_present;
    double average_magnitude;
    int max_vector_magnitude;
    const AVMotionVector *vectors;
    int vector_array_size;
} FrameSummary;

static void free_frame_summaries(FrameSummary *frames, int frame_count) {
    if (frames == NULL) {
        return;
    }
    for (int i = 0; i < frame_count; i++) {
        free((void *)frames[i].vectors);
    }
    free(frames);
}

static void json_escape(FILE *stream, const char *value) {
    fputc('"', stream);
    for (const unsigned char *cursor = (const unsigned char *)value; *cursor != '\0'; cursor++) {
        switch (*cursor) {
            case '\\':
                fputs("\\\\", stream);
                break;
            case '"':
                fputs("\\\"", stream);
                break;
            case '\b':
                fputs("\\b", stream);
                break;
            case '\f':
                fputs("\\f", stream);
                break;
            case '\n':
                fputs("\\n", stream);
                break;
            case '\r':
                fputs("\\r", stream);
                break;
            case '\t':
                fputs("\\t", stream);
                break;
            default:
                if (*cursor < 0x20) {
                    fprintf(stream, "\\u%04x", *cursor);
                } else {
                    fputc(*cursor, stream);
                }
        }
    }
    fputc('"', stream);
}

static int write_output(
    const char *output_path,
    const char *input_name,
    const char *input_path,
    FrameSummary *frames,
    int frame_count,
    int frames_with_vectors,
    int frames_with_motion_side_data,
    long long total_vectors,
    double total_magnitude
) {
    FILE *stream = fopen(output_path, "w");
    if (stream == NULL) {
        fprintf(stderr, "failed to open output %s: %s\n", output_path, strerror(errno));
        return 1;
    }

    fprintf(stream, "{\n");
    fprintf(stream, "  \"extractor_surface\": \"host libavcodec AV_FRAME_DATA_MOTION_VECTORS\",\n");
    fprintf(stream, "  \"input_name\": ");
    json_escape(stream, input_name);
    fprintf(stream, ",\n  \"source_path\": ");
    json_escape(stream, input_path);
    fprintf(stream, ",\n  \"frame_count\": %d,\n", frame_count);
    fprintf(stream, "  \"frames_with_vectors\": %d,\n", frames_with_vectors);
    fprintf(stream, "  \"frames_with_motion_side_data\": %d,\n", frames_with_motion_side_data);
    fprintf(stream, "  \"total_vectors\": %lld,\n", total_vectors);
    fprintf(stream, "  \"mean_vector_magnitude\": %.6f,\n", total_vectors > 0 ? total_magnitude / (double)total_vectors : 0.0);
    fprintf(stream, "  \"coordinate_vectors_available\": %s,\n", total_vectors > 0 ? "true" : "false");
    fprintf(stream, "  \"frames\": [\n");

    for (int i = 0; i < frame_count; i++) {
        FrameSummary *frame = &frames[i];
        fprintf(stream, "    {\n");
        fprintf(stream, "      \"frame_index\": %d,\n", frame->frame_index);
        fprintf(stream, "      \"timestamp\": %.6f,\n", frame->timestamp_seconds);
        fprintf(stream, "      \"pict_type\": ");
        char pict_type_buffer[2] = {frame->pict_type, '\0'};
        json_escape(stream, pict_type_buffer);
        fprintf(stream, ",\n      \"vector_count\": %d,\n", frame->vector_count);
        fprintf(stream, "      \"motion_vector_side_data_present\": %s,\n", frame->motion_vector_side_data_present ? "true" : "false");
        fprintf(stream, "      \"average_magnitude\": %.6f,\n", frame->average_magnitude);
        fprintf(stream, "      \"vectors\": [\n");

        for (int j = 0; j < frame->vector_array_size; j++) {
            const AVMotionVector *vector = &frame->vectors[j];
            fprintf(stream, "        {\n");
            fprintf(stream, "          \"source\": %d,\n", vector->source);
            fprintf(stream, "          \"w\": %d,\n", vector->w);
            fprintf(stream, "          \"h\": %d,\n", vector->h);
            fprintf(stream, "          \"src_x\": %d,\n", vector->src_x);
            fprintf(stream, "          \"src_y\": %d,\n", vector->src_y);
            fprintf(stream, "          \"dst_x\": %d,\n", vector->dst_x);
            fprintf(stream, "          \"dst_y\": %d,\n", vector->dst_y);
            fprintf(stream, "          \"motion_x\": %" PRId32 ",\n", vector->motion_x);
            fprintf(stream, "          \"motion_y\": %" PRId32 ",\n", vector->motion_y);
            fprintf(stream, "          \"motion_scale\": %u,\n", vector->motion_scale);
            fprintf(stream, "          \"flags\": %" PRIu64 "\n", vector->flags);
            fprintf(stream, "        }%s\n", j + 1 == frame->vector_array_size ? "" : ",");
        }
        fprintf(stream, "      ]\n");
        fprintf(stream, "    }%s\n", i + 1 == frame_count ? "" : ",");
    }

    fprintf(stream, "  ]\n}\n");
    fclose(stream);
    return 0;
}

static int decode_to_json(const char *input_path, const char *input_name, const char *output_path) {
    int result = 0;
    AVFormatContext *format_context = NULL;
    AVCodecContext *codec_context = NULL;
    AVPacket *packet = NULL;
    AVFrame *frame = NULL;
    FrameSummary *frames = NULL;
    int frame_capacity = 0;
    int frame_count = 0;
    int frames_with_vectors = 0;
    int frames_with_motion_side_data = 0;
    long long total_vectors = 0;
    double total_magnitude = 0.0;

    if ((result = avformat_open_input(&format_context, input_path, NULL, NULL)) < 0) {
        fprintf(stderr, "avformat_open_input failed: %d\n", result);
        return 1;
    }
    if ((result = avformat_find_stream_info(format_context, NULL)) < 0) {
        fprintf(stderr, "avformat_find_stream_info failed: %d\n", result);
        goto cleanup;
    }

    int stream_index = av_find_best_stream(format_context, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (stream_index < 0) {
        fprintf(stderr, "av_find_best_stream(video) failed: %d\n", stream_index);
        result = 1;
        goto cleanup;
    }

    AVStream *stream = format_context->streams[stream_index];
    const AVCodec *codec = avcodec_find_decoder(stream->codecpar->codec_id);
    if (codec == NULL) {
        fprintf(stderr, "avcodec_find_decoder failed for codec id %d\n", stream->codecpar->codec_id);
        result = 1;
        goto cleanup;
    }

    codec_context = avcodec_alloc_context3(codec);
    if (codec_context == NULL) {
        fprintf(stderr, "avcodec_alloc_context3 failed\n");
        result = 1;
        goto cleanup;
    }
    if ((result = avcodec_parameters_to_context(codec_context, stream->codecpar)) < 0) {
        fprintf(stderr, "avcodec_parameters_to_context failed: %d\n", result);
        goto cleanup;
    }
    codec_context->flags2 |= AV_CODEC_FLAG2_EXPORT_MVS;
    if ((result = avcodec_open2(codec_context, codec, NULL)) < 0) {
        fprintf(stderr, "avcodec_open2 failed: %d\n", result);
        goto cleanup;
    }

    packet = av_packet_alloc();
    frame = av_frame_alloc();
    if (packet == NULL || frame == NULL) {
        fprintf(stderr, "failed to allocate packet/frame\n");
        result = 1;
        goto cleanup;
    }

    while ((result = av_read_frame(format_context, packet)) >= 0) {
        if (packet->stream_index != stream_index) {
            av_packet_unref(packet);
            continue;
        }

        if ((result = avcodec_send_packet(codec_context, packet)) < 0) {
            fprintf(stderr, "avcodec_send_packet failed: %d\n", result);
            av_packet_unref(packet);
            goto cleanup;
        }
        av_packet_unref(packet);

        while ((result = avcodec_receive_frame(codec_context, frame)) >= 0) {
            if (frame_count == frame_capacity) {
                int new_capacity = frame_capacity == 0 ? 128 : frame_capacity * 2;
                FrameSummary *resized = realloc(frames, (size_t)new_capacity * sizeof(FrameSummary));
                if (resized == NULL) {
                    fprintf(stderr, "failed to allocate frame summary buffer\n");
                    result = 1;
                    goto cleanup;
                }
                frames = resized;
                frame_capacity = new_capacity;
            }

            FrameSummary *summary = &frames[frame_count];
            memset(summary, 0, sizeof(*summary));
            summary->frame_index = frame_count;
            summary->timestamp_seconds = frame->best_effort_timestamp == AV_NOPTS_VALUE
                ? 0.0
                : frame->best_effort_timestamp * av_q2d(stream->time_base);
            summary->pict_type = av_get_picture_type_char(frame->pict_type);

            AVFrameSideData *side_data = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
            if (side_data != NULL && side_data->size >= (int)sizeof(AVMotionVector)) {
                const AVMotionVector *source_vectors = (const AVMotionVector *)side_data->data;
                int vector_count = side_data->size / (int)sizeof(AVMotionVector);
                double frame_magnitude = 0.0;
                int max_magnitude = 0;
                AVMotionVector *copied_vectors = malloc((size_t)vector_count * sizeof(AVMotionVector));
                if (copied_vectors == NULL) {
                    fprintf(stderr, "failed to copy motion vectors for frame %d\n", frame_count);
                    result = 1;
                    goto cleanup;
                }
                memcpy(copied_vectors, source_vectors, (size_t)vector_count * sizeof(AVMotionVector));

                summary->motion_vector_side_data_present = 1;
                summary->vector_count = vector_count;
                summary->vector_array_size = vector_count;
                summary->vectors = copied_vectors;
                frames_with_motion_side_data += 1;

                for (int i = 0; i < vector_count; i++) {
                    double dx = (double)copied_vectors[i].dst_x - (double)copied_vectors[i].src_x;
                    double dy = (double)copied_vectors[i].dst_y - (double)copied_vectors[i].src_y;
                    double magnitude = hypot(dx, dy);
                    frame_magnitude += magnitude;
                    if ((int)magnitude > max_magnitude) {
                        max_magnitude = (int)magnitude;
                    }
                }

                summary->average_magnitude = vector_count > 0 ? frame_magnitude / (double)vector_count : 0.0;
                summary->max_vector_magnitude = max_magnitude;
                total_vectors += vector_count;
                total_magnitude += frame_magnitude;
                if (vector_count > 0) {
                    frames_with_vectors += 1;
                }
            }

            frame_count += 1;
            av_frame_unref(frame);
        }

        if (result == AVERROR(EAGAIN)) {
            continue;
        }
        if (result == AVERROR_EOF) {
            break;
        }
        if (result < 0) {
            fprintf(stderr, "avcodec_receive_frame failed: %d\n", result);
            goto cleanup;
        }
    }

    if (result == AVERROR_EOF) {
        result = 0;
    }

    if ((result = avcodec_send_packet(codec_context, NULL)) < 0) {
        fprintf(stderr, "avcodec_send_packet(flush) failed: %d\n", result);
        goto cleanup;
    }

    while ((result = avcodec_receive_frame(codec_context, frame)) >= 0) {
        if (frame_count == frame_capacity) {
            int new_capacity = frame_capacity == 0 ? 128 : frame_capacity * 2;
            FrameSummary *resized = realloc(frames, (size_t)new_capacity * sizeof(FrameSummary));
            if (resized == NULL) {
                fprintf(stderr, "failed to allocate frame summary buffer during flush\n");
                result = 1;
                goto cleanup;
            }
            frames = resized;
            frame_capacity = new_capacity;
        }
        FrameSummary *summary = &frames[frame_count];
        memset(summary, 0, sizeof(*summary));
        summary->frame_index = frame_count;
        summary->timestamp_seconds = frame->best_effort_timestamp == AV_NOPTS_VALUE
            ? 0.0
            : frame->best_effort_timestamp * av_q2d(stream->time_base);
        summary->pict_type = av_get_picture_type_char(frame->pict_type);

        AVFrameSideData *side_data = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
        if (side_data != NULL && side_data->size >= (int)sizeof(AVMotionVector)) {
            const AVMotionVector *source_vectors = (const AVMotionVector *)side_data->data;
            int vector_count = side_data->size / (int)sizeof(AVMotionVector);
            double frame_magnitude = 0.0;
            int max_magnitude = 0;
            AVMotionVector *copied_vectors = malloc((size_t)vector_count * sizeof(AVMotionVector));
            if (copied_vectors == NULL) {
                fprintf(stderr, "failed to copy motion vectors for frame %d during flush\n", frame_count);
                result = 1;
                goto cleanup;
            }
            memcpy(copied_vectors, source_vectors, (size_t)vector_count * sizeof(AVMotionVector));

            summary->motion_vector_side_data_present = 1;
            summary->vector_count = vector_count;
            summary->vector_array_size = vector_count;
            summary->vectors = copied_vectors;
            frames_with_motion_side_data += 1;

            for (int i = 0; i < vector_count; i++) {
                double dx = (double)copied_vectors[i].dst_x - (double)copied_vectors[i].src_x;
                double dy = (double)copied_vectors[i].dst_y - (double)copied_vectors[i].src_y;
                double magnitude = hypot(dx, dy);
                frame_magnitude += magnitude;
                if ((int)magnitude > max_magnitude) {
                    max_magnitude = (int)magnitude;
                }
            }

            summary->average_magnitude = vector_count > 0 ? frame_magnitude / (double)vector_count : 0.0;
            summary->max_vector_magnitude = max_magnitude;
            total_vectors += vector_count;
            total_magnitude += frame_magnitude;
            if (vector_count > 0) {
                frames_with_vectors += 1;
            }
        }

        frame_count += 1;
        av_frame_unref(frame);
    }

    if (result == AVERROR_EOF) {
        result = 0;
    } else if (result < 0 && result != AVERROR(EAGAIN)) {
        fprintf(stderr, "avcodec_receive_frame(flush) failed: %d\n", result);
        goto cleanup;
    }

    result = write_output(
        output_path,
        input_name,
        input_path,
        frames,
        frame_count,
        frames_with_vectors,
        frames_with_motion_side_data,
        total_vectors,
        total_magnitude
    );

cleanup:
    free_frame_summaries(frames, frame_count);
    av_frame_free(&frame);
    av_packet_free(&packet);
    avcodec_free_context(&codec_context);
    avformat_close_input(&format_context);
    return result == 0 ? 0 : 1;
}

int main(int argc, char **argv) {
    const char *input_path = NULL;
    const char *input_name = NULL;
    const char *output_path = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--input") == 0 && i + 1 < argc) {
            input_path = argv[++i];
        } else if (strcmp(argv[i], "--input-name") == 0 && i + 1 < argc) {
            input_name = argv[++i];
        } else if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            output_path = argv[++i];
        } else {
            fprintf(stderr, "unknown or incomplete argument: %s\n", argv[i]);
            return 1;
        }
    }

    if (input_path == NULL || input_name == NULL || output_path == NULL) {
        fprintf(stderr, "usage: %s --input <path> --input-name <name> --output <path>\n", argv[0]);
        return 1;
    }

    av_log_set_level(AV_LOG_ERROR);
    return decode_to_json(input_path, input_name, output_path);
}
