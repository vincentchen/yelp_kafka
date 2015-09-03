import pytest
import mock

from yelp_kafka import discovery
from yelp_kafka.config import ClusterConfig
from yelp_kafka.error import DiscoveryError


@pytest.fixture
def mock_clusters():
    return [
        ClusterConfig('type1', 'cluster1', ['mybroker'], 'zk_hosts/kafka'),
        ClusterConfig('type1', 'cluster2', ['mybroker2'], 'zk_hosts2/kafa'),
    ]


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
def test_get_local_cluster(mock_topology):
    get_cluster = mock_topology.return_value.get_local_cluster
    get_cluster.return_value = mock.sentinel.cluster
    cluster = discovery.get_local_cluster("mycluster")
    mock_topology.assert_called_once_with(cluster_type='mycluster')
    get_cluster.assert_called_once_with()
    assert cluster == mock.sentinel.cluster


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
def test_get_all_clusters(mock_topology):
    get_clusters = mock_topology.return_value.get_all_clusters
    get_clusters.return_value = mock.sentinel.clusters
    clusters = discovery.get_all_clusters("mycluster")
    mock_topology.assert_called_once_with(cluster_type='mycluster')
    get_clusters.assert_called_once_with()
    assert clusters == mock.sentinel.clusters


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
def test_get_cluster_by_name(mock_topology):
    get_cluster_by_name = mock_topology.return_value.get_cluster_by_name
    get_cluster_by_name.return_value = mock.sentinel.cluster
    cluster = discovery.get_cluster_by_name("mycluster", "myname")
    mock_topology.assert_called_once_with(cluster_type='mycluster')
    get_cluster_by_name.assert_called_once_with('myname')
    assert cluster == mock.sentinel.cluster


@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_get_consumer_config(mock_get_cluster):
    my_cluster = ClusterConfig(
        'type1',
        'cluster1',
        ['mybroker'],
        'zk_hosts/kafka',
    )
    mock_get_cluster.return_value = my_cluster
    with mock.patch("yelp_kafka.discovery.KafkaConsumerConfig",
                    autospec=True) as mock_config:
        mock_config.return_value = mock.sentinel.kafka_config
        actual = discovery.get_consumer_config(
            "mycluster", group_id='mygroup', auto_offset_reset='largest')
        mock_config.assert_called_once_with(
            cluster=my_cluster, group_id='mygroup',
            auto_offset_reset='largest'
        )
        assert actual == mock.sentinel.kafka_config


@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_get_all_consumer_config(mock_get_clusters, mock_clusters):
    mock_get_clusters.return_value = mock_clusters
    with mock.patch("yelp_kafka.discovery.KafkaConsumerConfig",
                    autospec=True) as mock_config:
        mock_config.return_value = mock.sentinel.kafka_config
        actual = discovery.get_all_consumer_config(
            "mycluster", group_id='mygroup', auto_offset_reset='largest')
        assert mock_config.call_args_list == [
            mock.call(cluster=mock_clusters[0], group_id='mygroup',
                      auto_offset_reset='largest'),
            mock.call(cluster=mock_clusters[1], group_id='mygroup',
                      auto_offset_reset='largest'),
        ]
        assert actual == [mock.sentinel.kafka_config,
                          mock.sentinel.kafka_config]


@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_get_kafka_connection(mock_get_cluster):
    my_cluster = ClusterConfig(
        'type1',
        'cluster1',
        ['mybroker'],
        'zk_hosts/kafka',
    )
    mock_get_cluster.return_value = my_cluster
    with mock.patch("yelp_kafka.discovery.KafkaClient",
                    autospec=True) as mock_kafka:
        mock_kafka.return_value = mock.sentinel.kafkaclient
        actual = discovery.get_kafka_connection("mycluster")
        mock_kafka.assert_called_once_with(['mybroker'],
                                           client_id='yelp-kafka')
        assert actual == mock.sentinel.kafkaclient


@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_get_kafka_connection_error(mock_get_cluster):
    my_cluster = ClusterConfig(
        'type1',
        'cluster1',
        ['mybroker'],
        'zk_hosts/kafka',
    )
    mock_get_cluster.return_value = my_cluster
    with mock.patch("yelp_kafka.discovery.KafkaClient",
                    autospec=True) as mock_kafka:
        mock_kafka.side_effect = Exception("Boom!")
        with pytest.raises(DiscoveryError):
            discovery.get_kafka_connection("mycluster")
        mock_kafka.assert_called_once_with(['mybroker'],
                                           client_id='yelp-kafka')


@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_get_all_kafka_connections(mock_get_clusters, mock_clusters):
    mock_get_clusters.return_value = mock_clusters
    with mock.patch("yelp_kafka.discovery.KafkaClient",
                    autospec=True) as mock_kafka:
        mock_kafka.return_value = mock.sentinel.kafkaclient
        actual = discovery.get_all_kafka_connections("mycluster")
        assert mock_kafka.call_args_list == [
            mock.call(['mybroker'], client_id='yelp-kafka'),
            mock.call(['mybroker2'], client_id='yelp-kafka')
        ]
        assert actual == [('cluster1', mock.sentinel.kafkaclient),
                          ('cluster2', mock.sentinel.kafkaclient)]


@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_get_all_kafka_connections_error(mock_get_clusters, mock_clusters):
    mock_get_clusters.return_value = mock_clusters
    with mock.patch("yelp_kafka.discovery.KafkaClient",
                    autospec=True) as mock_kafka:
        client = mock.MagicMock()
        mock_kafka.side_effect = [client, Exception("Boom!")]
        with pytest.raises(DiscoveryError):
            discovery.get_all_kafka_connections("mycluster")
        client.close.assert_called_once_with()


@mock.patch("yelp_kafka.discovery.get_kafka_topics", autospec=True)
@mock.patch("yelp_kafka.discovery.KafkaClient", autospec=True)
def test_discover_topics(mock_kafka, mock_topics):
    expected = {
        'topic1': [0, 1, 2, 3],
        'topic2': [0]
    }
    mock_topics.return_value = expected
    actual = discovery.discover_topics(ClusterConfig(
        'type1',
        'mycluster',
        ['mybroker'],
        'zkhosts/kakfa',
    ))
    assert actual == expected


@mock.patch("yelp_kafka.discovery.get_kafka_topics", autospec=True)
@mock.patch("yelp_kafka.discovery.KafkaClient", autospec=True)
def test_discover_topics_error(mock_kafka, mock_topics):
    mock_topics.side_effect = Exception("Boom!")
    with pytest.raises(DiscoveryError):
        discovery.discover_topics(
            ClusterConfig('type1', 'mycluster', ['mybroker'], 'zkhosts')
        )


def test_search_topic(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {'topic1': [0, 1, 2], 'topic2': [0]}
        ])
        # topic1 is only in the first cluster
        actual = discovery.search_topic('topic1', [mock_clusters[0]])
        expected = [('topic1', mock_clusters[0])]
        assert expected == actual


def test_search_topic_in_2_clusters(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {'topic1': [0, 1, 2], 'topic2': [0]},
            {'topic2': [0]}
        ])
        # topic1 is only in cluster1
        actual = discovery.search_topic('topic2', mock_clusters)
        expected = [('topic2', mock_clusters[0]),
                    ('topic2', mock_clusters[1])]
        assert expected == actual


def test_search_no_topic(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {'topic1': [0, 1, 2], 'topic2': [0]},
            {'topic2': [0]}
        ])
        actual = discovery.search_topic('topic3', mock_clusters)
        # Since the topic does not exist we expect an empty list
        assert [] == actual


@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_local_topic_exists(mock_get_cluster, mock_search):
    mock_get_cluster.return_value = mock.sentinel.cluster
    mock_search.return_value = [mock.sentinel.topic]
    actual = discovery.local_topic_exists('mycluster', 'topic1')
    mock_search.assert_called_once_with('topic1', [mock.sentinel.cluster])
    assert actual is True


@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_local_topic_not_exists(mock_get_cluster, mock_search):
    mock_get_cluster.return_value = mock.sentinel.cluster
    mock_search.return_value = []
    actual = discovery.local_topic_exists('mycluster', 'topic1')
    mock_search.assert_called_once_with('topic1', [mock.sentinel.cluster])
    assert actual is False


@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_search_topics_in_all_clusters(mock_get_clusters, mock_search):
    mock_get_clusters.return_value = mock.sentinel.clusters
    mock_search.return_value = mock.sentinel.topics
    actual = discovery.search_topic_in_all_clusters(
        'mycluster', 'topic1'
    )
    mock_get_clusters.assert_called_once_with('mycluster')
    mock_search.assert_called_once_with('topic1', mock.sentinel.clusters)
    assert actual == mock.sentinel.topics


@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_search_topics_no_topics_in_clusters(mock_get_clusters, mock_search):
    mock_get_clusters.return_value = mock.sentinel.clusters
    mock_search.return_value = []
    with pytest.raises(DiscoveryError):
        discovery.search_topic_in_all_clusters(
            'mycluster', 'topic1'
        )
    mock_get_clusters.assert_called_once_with('mycluster')
    mock_search.assert_called_once_with('topic1', mock.sentinel.clusters)


def test_search_by_regex(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {'topic1': [0, 1, 2], 'topic2': [0]},
            {'topic2': [0]}
        ])
        # search for all topics starting with top
        actual = discovery.search_topics_by_regex('top.*', mock_clusters)
        expected = [(['topic1', 'topic2'], mock_clusters[0]),
                    (['topic2'], mock_clusters[1])]

        assert len(expected) == len(actual)
        for expected_topic in expected:
            assert any(
                sorted(actual_topic[0]) == sorted(expected_topic[0]) and
                actual_topic[1] == actual_topic[1]
                for actual_topic in actual
            )


def test_search_by_scribe_regex(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {
                'scribe..topic1': [0, 1, 2],
                'scribe.dev.topic1': [0],
            },
            {
                'scribe.uswest1-dev.topic1': [0],
                'scribe.uswest1-dev.topic2': [0],
            }
        ])
        # search for all topics starting with top
        pattern = discovery.make_scribe_regex('topic1')
        actual = discovery.search_topics_by_regex(pattern, mock_clusters)
        expected = [
            (['scribe.dev.topic1'], mock_clusters[0]),
            (['scribe.uswest1-dev.topic1'], mock_clusters[1]),
        ]

        assert len(expected) == len(actual)
        for expected_topic in expected:
            assert any(
                sorted(actual_topic[0]) == sorted(expected_topic[0]) and
                actual_topic[1] == actual_topic[1]
                for actual_topic in actual
            )


@mock.patch("yelp_kafka.discovery.search_local_topics_by_regex")
def test_search_local_scribe_topics_by_regex(mock_search):
    discovery.search_local_scribe_topics_by_regex(".*")
    mock_search.assert_called_once_with("scribe", "scribe\\.devc\\..*")


def test_search_by_regex_no_topic(mock_clusters):
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([
            {'topic1': [0, 1, 2], 'topic2': [0]},
            {'topic2': [0]}
        ])
        # search for all topics starting with top
        actual = discovery.search_topics_by_regex('notopic.*', mock_clusters)
        assert [] == actual


@mock.patch("yelp_kafka.discovery.search_topics_by_regex", autospec=True)
@mock.patch("yelp_kafka.discovery.get_local_cluster", autospec=True)
def test_search_local_topic_by_regex(mock_get_cluster, mock_search):
    mock_get_cluster.return_value = mock.sentinel.cluster
    mock_search.return_value = [mock.sentinel.topics]
    actual = discovery.search_local_topics_by_regex(
        'mycluster', 'topic1.*'
    )
    mock_search.assert_called_once_with('topic1.*', [mock.sentinel.cluster])
    assert actual == mock.sentinel.topics


@mock.patch("yelp_kafka.discovery.search_topics_by_regex", autospec=True)
@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_search_topic_by_regex_in_all_clusters(mock_get_clusters, mock_search):
    mock_get_clusters.return_value = mock.sentinel.clusters
    mock_search.return_value = mock.sentinel.topics
    actual = discovery.search_topics_by_regex_in_all_clusters(
        'mycluster', 'topic1.*'
    )
    mock_search.assert_called_once_with('topic1.*', mock.sentinel.clusters)
    mock_get_clusters.assert_called_once_with('mycluster')
    assert actual == mock.sentinel.topics


@mock.patch("yelp_kafka.discovery.search_topics_by_regex", autospec=True)
@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_search_topic_by_regex_in_all_clusters_error(
    mock_get_clusters,
    mock_search
):
    mock_get_clusters.return_value = mock.sentinel.clusters
    mock_search.return_value = []
    with pytest.raises(DiscoveryError):
        discovery.search_topics_by_regex_in_all_clusters(
            'mycluster', 'topic1.*'
        )
    mock_search.assert_called_once_with('topic1.*', mock.sentinel.clusters)
    mock_get_clusters.assert_called_once_with('mycluster')


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
def test_get_local_scribe_topic(mock_search, mock_top):
    my_cluster = (
        'cluster1',
        {'broker_list': ['mybroker'], 'zookeeper': 'zk_hosts/kafka'}
    )
    mock_top.return_value.get_local_cluster.return_value = my_cluster
    mock_top.return_value.get_scribe_local_prefix.return_value = 'my.prefix.'
    mock_search.return_value = [mock.sentinel.topic]
    actual = discovery.get_local_scribe_topic('ranger')
    assert actual == mock.sentinel.topic
    mock_search.assert_called_once_with(
        'my.prefix.ranger', [my_cluster]
    )


@mock.patch("yelp_kafka.discovery.search_local_topics_by_regex", autospec=True)
def test_get_all_local_scribe_topics(mock_search):
    mock_search.return_value = (
        [mock.sentinel.topic1, mock.sentinel.topic2],
        mock.sentinel.cluster,
    )
    topics, cluster = discovery.get_all_local_scribe_topics('ranger')
    assert topics == [mock.sentinel.topic1, mock.sentinel.topic2]
    assert cluster == mock.sentinel.cluster
    mock_search.assert_called_once_with(
        discovery.DEFAULT_KAFKA_SCRIBE,
        '^scribe\.[\w-]+\.ranger$',
    )


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
def test_local_scribe_topic_exists(mock_search, mock_top):
    my_cluster = (
        'cluster1',
        {'broker_list': ['mybroker'], 'zookeeper': 'zk_hosts/kafka'}
    )
    mock_top.return_value.get_local_cluster.return_value = my_cluster
    mock_top.return_value.get_scribe_local_prefix.return_value = 'my.prefix.'
    mock_search.return_value = [mock.sentinel.topic]
    actual = discovery.local_scribe_topic_exists('ranger')
    assert actual is True
    mock_search.assert_called_once_with(
        'my.prefix.ranger', [my_cluster]
    )


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
def test_local_scribe_topic_not_exists(mock_search, mock_top):
    my_cluster = (
        'cluster1',
        {'broker_list': ['mybroker'], 'zookeeper': 'zk_hosts/kafka'}
    )
    mock_top.return_value.get_local_cluster.return_value = my_cluster
    mock_top.return_value.get_scribe_local_prefix.return_value = 'my.prefix.'
    mock_search.return_value = []
    actual = discovery.local_scribe_topic_exists('ranger')
    assert actual is False
    mock_search.assert_called_once_with(
        'my.prefix.ranger', [my_cluster]
    )


@mock.patch("yelp_kafka.discovery.TopologyConfiguration", autospec=True)
@mock.patch("yelp_kafka.discovery.search_topic", autospec=True)
def test_get_local_scribe_topic_error(mock_search, mock_top):
    my_cluster = (
        'cluster1',
        {'broker_list': ['mybroker'], 'zookeeper': 'zk_hosts/kafka'}
    )
    mock_top.return_value.get_local_cluster.return_value = my_cluster
    mock_top.return_value.get_scribe_local_prefix.return_value = 'my.prefix.'
    mock_search.return_value = []
    with pytest.raises(DiscoveryError):
        discovery.get_local_scribe_topic('ranger')
    mock_search.assert_called_once_with(
        'my.prefix.ranger', [my_cluster]
    )


@mock.patch("yelp_kafka.discovery.search_topic_in_all_clusters", autospec=True)
def test_scribe_topic_exists_in_datacenter(mock_search):
    mock_search.return_value = [mock.sentinel.topics]
    actual = discovery.scribe_topic_exists_in_datacenter('ranger', 'sfo2')
    assert actual is True
    mock_search.assert_called_once_with(
        discovery.DEFAULT_KAFKA_SCRIBE, 'scribe.sfo2.ranger'
    )


@mock.patch("yelp_kafka.discovery.search_topic_in_all_clusters", autospec=True)
def test_scribe_topic_not_exists_in_datacenter(mock_search):
    mock_search.return_value = []
    actual = discovery.scribe_topic_exists_in_datacenter('ranger', 'sfo2')
    assert actual is False
    mock_search.assert_called_once_with(
        discovery.DEFAULT_KAFKA_SCRIBE, 'scribe.sfo2.ranger'
    )


@mock.patch("yelp_kafka.discovery.search_topic_in_all_clusters", autospec=True)
def test_get_scribe_topic_in_datacenter(mock_search):
    mock_search.return_value = [mock.sentinel.topics]
    actual = discovery.get_scribe_topic_in_datacenter('ranger', 'sfo2')
    assert actual == mock.sentinel.topics
    mock_search.assert_called_once_with(
        discovery.DEFAULT_KAFKA_SCRIBE, 'scribe.sfo2.ranger'
    )


@mock.patch("yelp_kafka.discovery.search_topic_in_all_clusters", autospec=True)
def test_get_scribe_topic_in_datacenter_error(mock_search):
    mock_search.return_value = []
    with pytest.raises(DiscoveryError):
        discovery.get_scribe_topic_in_datacenter('ranger', 'sfo2')
    mock_search.assert_called_once_with(
        discovery.DEFAULT_KAFKA_SCRIBE, 'scribe.sfo2.ranger'
    )


@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_get_scribe_topic(mock_get_clusters, mock_clusters):
    mock_get_clusters.return_value = mock_clusters
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([{
            'scribe.dc1.my_scribe_stream2': [0, 1, 2],
            'scribe.dc1.my_scribe_stream': [0, 1, 2],
            'scribe.dc2.my_scribe_stream': [0]
        }, {
            'scribe.dc1.non_my_scribe_stream': [0, 1]
        }])
        expected = (
            [
                'scribe.dc2.my_scribe_stream',
                'scribe.dc1.my_scribe_stream',
            ],
            mock_clusters[0],
        )
        actual = discovery.get_scribe_topics('my_scribe_stream')

    # actual should be a list containing the expected tuple
    assert len(actual) == 1
    assert (sorted(actual[0][0]) == sorted(expected[0]) and
            actual[0][1] == expected[1])


@mock.patch("yelp_kafka.discovery.get_all_clusters", autospec=True)
def test_get_scribe_topic_error(mock_get_clusters, mock_clusters):
    mock_get_clusters.return_value = mock_clusters
    with mock.patch("yelp_kafka.discovery.discover_topics",
                    autospec=True) as mock_discover:
        mock_discover.side_effect = iter([{
            'scribe.dc1.my_scribe_stream2': [0, 1, 2],
            'scribe.dc1.my_scribe_stream': [0, 1, 2],
            'scribe.dc2.my_scribe_stream': [0]
        }, {
            'scribe.dc1.non_my_scribe_stream': [0, 1]
        }])
        with pytest.raises(DiscoveryError):
            discovery.get_scribe_topics('not_a_real_stream')
